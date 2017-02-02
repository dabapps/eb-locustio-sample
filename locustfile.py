import os
from locust import HttpLocust, TaskSet, task, web
from slurping_smtpd import NO_EMAIL_AVAILABLE, TEAM_MEMBER_NOT_AVAILABLE, SMTPD_PORT, get_last_message_for, get_next_team_member, get_smtpd_status_info
from bs4 import BeautifulSoup
import uuid
import random
from slugify import slugify
import re
import requests
from datetime import datetime
import flask
# import xlwt
import io
from openpyxl import Workbook


FIRST_NAMES = ("Han", "Leia", "Chewy", "Luke", "Boba", "Ben")
SECOND_NAMES = ("Solo", "Skywalker", "Fett", "Hutt")

CUSTOM_FILTERS = {
    'Filter1': ['Foo', 'Bar', 'Baz'],
    'Filter2': ['Foo', 'Bar', 'Baz'],
    'Filter3': ['Foo', 'Bar', 'Baz'],
    'Filter4': ['Foo', 'Bar', 'Baz'],
    'Filter5': ['Foo', 'Bar', 'Baz'],
    'Filter6': ['Foo', 'Bar', 'Baz'],
}

TEAM_NAMES = ["Team 1", "Team 2", ]
LOCATIONS = ["Brighton", "London", ]
DEPTS = ["IT", "Ops", "PR", "Marketing", ]
LANGUAGES = ["English", ]


# MASTER_IP = requests.get("http://169.254.169.254/latest/meta-data/public-hostname", timeout=10).content
MASTER_IP = "127.0.0.1"
MASTER_PORT = os.getenv("MASTER_PORT", "80")

try:
    with open(".masterIP", 'r') as master_ip_file:
        MASTER_IP = master_ip_file.read()
        print("Found .masterIP file - using its value: {}".format(MASTER_IP))
except IOError:
    pass

print("MASTER_IP: {}\nMASTER_PORT: {}\n".format(MASTER_IP, MASTER_PORT))


URL_PLACEHOLDER_MATCHERS = (
    (re.compile(r"\/\d+\/"), "/[id]/"),   # pure numeric id
    (re.compile(r"/[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89aAbB][a-f0-9]{3}-[a-f0-9]{12}/"), "/[uuid]/"),   # UUID id
    (re.compile(r"/[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89aAbB][a-f0-9]{3}-[a-f0-9]{12}"), "/[uuid]"),   # UUID id
    (re.compile(r"/[a-f0-9]{40}/"), "/[token]/"),   # not sure
    (re.compile(r"http:\/\/[^\/]+\/"), "/"),   # remove domain prefix (if any)
    (re.compile(r"https:\/\/[^\/]+\/"), "/"),   # remove domain prefix (if any)
)


def create_placeholdered_url_for_stats(full_url):
    """
    We need to create consistent and generic URLs to display in the
    stats for Locust. This is a generic routine that attempts to
    replace any ID's with a placeholder name, and remove domains
    and add a starting slash - just to keep it all consistent.
    """
    placheholdered_url = full_url
    for (pattern, replacement) in URL_PLACEHOLDER_MATCHERS:
        placheholdered_url = pattern.sub(replacement, placheholdered_url)
    if placheholdered_url[0] != '/':
        placheholdered_url = '/' + placheholdered_url
    return placheholdered_url


def generate_random_email_and_name():
    first_name = random.choice(FIRST_NAMES)
    second_name = random.choice(SECOND_NAMES)
    return (
        "{}.{}+{}@example.com".format(
            slugify(first_name),
            slugify(second_name),
            str(uuid.uuid4())
        ),
        "{} {}".format(first_name, second_name)
    )


def generate_team():
    return random.choice(TEAM_NAMES)


def generate_location():
    return random.choice(LOCATIONS)


def generate_dept():
    return random.choice(DEPTS)


def generate_langauge():
    return random.choice(LANGUAGES)


def generate_random_team_member():
    (email, name) = generate_random_email_and_name()
    return (
        email,
        name,
        generate_team(),
        generate_location(),
        generate_dept(),
        generate_langauge(),
    )


def create_team_member_excel_file(num_team_members):
    book = Workbook()
    sheet1 = book.active
    sheet1.append(("Email", "Name", "Team", "Location", "Department", "Language"))
    for i in range(0, num_team_members):
        sheet1.append(generate_random_team_member())
    raw_xls = io.BytesIO()
    print(book)
    book.save(raw_xls)
    return raw_xls.getvalue()


def remove_current_index_rule_so_we_can_replace_it():
    for rule in web.app.url_map._rules:
        print(rule.endpoint)
        if rule.endpoint == 'index':
            web.app.url_map._rules.remove(rule)
            print('REMOVED ORIG / RULE')

remove_current_index_rule_so_we_can_replace_it()


def smtp_info():
    return "EMAIL_HOST={}\nEMAIL_HOST_PASSWORD={}\nEMAIL_HOST_USER={}\nEMAIL_PORT={}\nEMAIL_USE_TLS=False".format(
        flask.request.environ['HTTP_HOST'],
        "",
        "",
        SMTPD_PORT
    )


def target_info():
    return "TARGET_URL = {}".format(os.getenv('TARGET_URL', "http://localhost"))


def extra_info():
    return [target_info(), smtp_info(), get_smtpd_status_info()]


@web.app.route("/")
def www_index():
    extra_html = "<hr />".join(extra_info())
    html = web.index()  # the original index page
    html = html.replace('<div class="main">', '<small><pre>{}</pre></small><div class="main">'.format(extra_html))
    return html


@web.app.route("/env")
def www_env():
    return "<pre>{}</pre><hr /><pre>{}</pre>".format(
        "\n".join(["{} = \"{}\"".format(k, v) for (k, v) in os.environ.items()]),
        flask.request.environ
    )


@web.app.route("/get_last_message_for/<email_address>")
def www_get_last_message_for(email_address):
    return get_last_message_for(email_address)


@web.app.route("/get_next_team_member")
def www_get_next_team_member():
    return get_next_team_member()


class CompleteSurvey(TaskSet):

    def on_start(self):
        print("CompleteSurvey: on_start")
        self.schedule_task(self._fetch_team_member_details_from_master)

    def _fetch_team_member_details_from_master(self, retry_count=0):
        print("CompleteSurvey: _fetch_team_member_details_from_master")
        request_1 = requests.get("http://{}:{}/get_next_team_member".format(MASTER_IP, MASTER_PORT))
        message = request_1.text
        if TEAM_MEMBER_NOT_AVAILABLE not in message:
            survey_url = message
            self.schedule_task(self._fill_in_survey, args=[survey_url, ])
        else:
            # if retry_count < 5:    # Obvs not enough surveys, so potentially become a survey maker.
            self.schedule_task(self._fetch_team_member_details_from_master, args=[retry_count + 1, ])

    def _fill_in_survey(self, survey_url):
        print("CompleteSurvey: _fill_in_survey - {}".format(survey_url))
        self.schedule_task(self._get_first_page, args=[survey_url, ])

    def _extract_form_into_dict(self, content):
        soup = BeautifulSoup(content, 'html.parser')
        form = soup.form
        if form:  # survey open?
            data = {}
            for input_tag in form.find_all('input'):
                try:
                    data[input_tag['name']] = input_tag['value']
                except KeyError:
                    pass
            print(data)
            return data

    def _fill_in_survey_form(self, content):
        data = self._extract_form_into_dict(content)
        if data:
            for k, v in data.items():
                if '-Q' in k:
                    data[k] = "5"
        return data

    def _get_first_page(self, page_url):
        print("_get_first_page: {}".format(page_url))
        response_1 = self.client.get(page_url,
                                     name=create_placeholdered_url_for_stats(page_url))
        data = self._fill_in_survey_form(response_1.content)
        if data is not None:
            self.schedule_task(self._fill_in_subsequent_pages, args=[response_1.url, data])
        else:
            print("No form in survey - survey closed or already completed?")
            print(response_1.content)

    def _fill_in_subsequent_pages(self, page_url, data):
        print("_fill_in_subsequent_pages: {}".format(page_url))
        response_1 = self.client.post(page_url,
                                      data,
                                      name=create_placeholdered_url_for_stats(page_url))
        data = self._fill_in_survey_form(response_1.content)
        if data is not None:
            self.schedule_task(self._fill_in_subsequent_pages, args=[response_1.url, data])
        else:
            print("No form in survey - survey finished?")

    @task
    def stop(self):
        print('stop')
        self.interrupt()


class CreateSurvey(TaskSet):

    def on_start(self):
        print("CreateSurvey: on_start")
        # Get CSRF token
        response_1 = self.client.get("accounts/register/")
        soup = BeautifulSoup(response_1.content, 'html.parser')
        csrfmiddlewaretoken = soup.form.input['value']
        (random_email, random_name) = generate_random_email_and_name()
        data = {
            "csrfmiddlewaretoken": csrfmiddlewaretoken,
            "email": random_email,
            "first_name": random_name,
        }
        print(data)
        response_2 = self.client.post("accounts/register/", data)
        response_2
        # print(response_2.content)

        self.schedule_task(self._wait_for_signup_email, args=[random_name, random_email])

    def _wait_for_signup_email(self, name, email):
        print('wait_for_email ({}  {})'.format(name, email))
        request_1 = requests.get("http://{}:{}/get_last_message_for/{}".format(MASTER_IP, MASTER_PORT, email))
        message = request_1.text
        if message != NO_EMAIL_AVAILABLE:
            print('GOT MESSAGE!')
            # print(message)
            matches = re.search("(account/activate/[^\/]+/)", message, re.MULTILINE)
            if matches:
                finish_signup_url = matches.group(1)
                self.schedule_task(self._finish_signup, args=[name, email, finish_signup_url])
            else:
                raise Exception("Unable to extract activation link! {}".format(message))
        else:
            self.schedule_task(self._wait_for_signup_email, args=[name, email])

    def _finish_signup(self, name, email, finish_signup_url):
        print('_finish_signup {}'.format(finish_signup_url))
        response_1 = self.client.get(finish_signup_url,
                                     name=create_placeholdered_url_for_stats(finish_signup_url))
        soup = BeautifulSoup(response_1.content, 'html.parser')
        csrfmiddlewaretoken = soup.form.input['value']
        password = "password1!"
        data = {
            "csrfmiddlewaretoken": csrfmiddlewaretoken,
            "new_password": password,
            "confirm_password": password,
        }
        print(response_1.url)
        print(data)
        response_2 = self.client.post(response_1.url,  # noqa
                                      data,
                                      name=create_placeholdered_url_for_stats(response_1.url))  # noqa
        # response_2
        # print(response_2.content)

        self.schedule_task(self._login, args=[email, password])

    def _login(self, email, password):
        response_1 = self.client.get("accounts/login/")
        soup = BeautifulSoup(response_1.content, 'html.parser')
        csrfmiddlewaretoken = soup.form.input['value']
        data = {
            "csrfmiddlewaretoken": csrfmiddlewaretoken,
            "username": email,
            "password": password,
            "next": "/people/",
        }
        print(data)
        response_2 = self.client.post('accounts/login/', data)  # noqa
        # print(response_2)

        # for filter_name, tag_names in CUSTOM_FILTERS.items():
        #     self.schedule_task(self._add_custom_filters, args=[filter_name, tag_names])
        # self.schedule_task(self._create_team)
        self.schedule_task(self._create_team_excel)
        self.schedule_task(self._create_survey)

    def _add_custom_filters(self, filter_name, tag_names):
        response_1 = self.client.get('manage_filters/')
        soup = BeautifulSoup(response_1.content, 'html.parser')
        csrfmiddlewaretoken = soup.form.input['value']
        data = {
            "csrfmiddlewaretoken": csrfmiddlewaretoken,
            "user": 1371,
            "category_name": filter_name,
            "verb": "Create Filter",
        }
        print(data)
        response_2 = self.client.post(response_1.url, data)  # noqa
        manage_tag_url = response_2.url

        for tag_name in tag_names:
            response_3 = self.client.get(manage_tag_url)
            soup = BeautifulSoup(response_3.content, 'html.parser')
            csrfmiddlewaretoken = soup.form.input['value']
            data = {
                "csrfmiddlewaretoken": csrfmiddlewaretoken,
                "name": tag_name,
                "verb": "Add",
            }
            print(data)
            response_4 = self.client.post(response_3.url, data)  # noqa
            manage_tag_url = response_4.url

    def _create_team_excel(self):
        num_team_members_to_create = random.choice([100, 200, 1500])

        response_1 = self.client.get("people/import_people/")
        soup = BeautifulSoup(response_1.content, 'html.parser')
        csrfmiddlewaretoken = soup.form.input['value']
        data = {
            "csrfmiddlewaretoken": csrfmiddlewaretoken,
            "verb": "Upload",
        }
        print(data)
        response_2 = self.client.post(response_1.url,
                                      name=create_placeholdered_url_for_stats(
                                          response_1.url + (" ({} members)".format(num_team_members_to_create))
                                      ),
                                      data=data,
                                      files={'excel_people_list': ('members.xlsx', create_team_member_excel_file(num_team_members_to_create))})
        print(response_2.content)

    def _create_team(self):
        num_team_members_to_create = random.choice([100, 200, 1500])

        # batch create them 200 at a time
        batch_size = 200  # 250 (actually 248) is max for this method
        while num_team_members_to_create > 0:
            response_1 = self.client.get("people/")
            soup = BeautifulSoup(response_1.content, 'html.parser')
            csrfmiddlewaretoken = soup.form.input['value']
            team_members_email_addresses_csv = "\n".join([",".join(generate_random_team_member()) for x in range(0, batch_size)])
            data = {
                "csrfmiddlewaretoken": csrfmiddlewaretoken,
                "email_addresses": team_members_email_addresses_csv,
                "verb": "Add",
            }
            print(data)
            response_2 = self.client.post('people/', data, name="/people/ ({} members)".format(batch_size))  # noqa
            # print(response_2.content)
            num_team_members_to_create -= batch_size

    def _create_survey(self):
        self.client.get("surveys/")

        response_1 = self.client.get("surveys/create/")
        soup = BeautifulSoup(response_1.content, 'html.parser')
        csrfmiddlewaretoken = soup.form.input['value']
        now = datetime.now()
        date_today = now.strftime("%d/%m/%Y")
        time_now = now.strftime("%H:%M")
        data = {
            "csrfmiddlewaretoken": csrfmiddlewaretoken,
            "auto_close_date": date_today,
            "name": "Survey Name",
            "company_name": "Company Name",
            "auto_start_date": date_today,
            "start_time": time_now,
            "end_date_week": 1,
            "auto_nudge_enabled": "on",
        }
        print(data)
        response_2 = self.client.post('surveys/create/', data)  # noqa
        choose_team_to_send_survey_to_url = response_2.url

        self.schedule_task(self._choose_team_to_send_survey_to_url, args=[choose_team_to_send_survey_to_url, ])

    def _choose_team_to_send_survey_to_url(self, choose_team_to_send_survey_to_url):
        print(choose_team_to_send_survey_to_url)
        response_1 = self.client.get(choose_team_to_send_survey_to_url,
                                     name=create_placeholdered_url_for_stats(
                                         choose_team_to_send_survey_to_url
                                     ))
        soup = BeautifulSoup(response_1.content, 'html.parser')
        forms = soup.find_all('form')
        # print(forms)
        form = forms[1]  # # NOTE: It's the 2nd form on this page !?
        data = {}
        for input_tag in form.find_all('input'):
            try:
                name = input_tag['name']
                if '_added' in name:
                    data[name] = "on"
                else:
                    data[name] = input_tag['value']
            except KeyError:
                # some inputs dont have a 'name' attr
                pass
        print(data)
        response_2 = self.client.post(response_1.url,  # noqa
                                      data,
                                      name=create_placeholdered_url_for_stats(response_1.url))  # noqa
        preview_survey_url = response_2.url

        self.schedule_task(self._preview_survey, args=[preview_survey_url, ])

    def _preview_survey(self, preview_survey_url):
        response_1 = self.client.get(preview_survey_url,
                                     name=create_placeholdered_url_for_stats(preview_survey_url))
        soup = BeautifulSoup(response_1.content, 'html.parser')
        csrfmiddlewaretoken = soup.form.input['value']
        data = {
            "csrfmiddlewaretoken": csrfmiddlewaretoken,
        }
        print(data)
        response_2 = self.client.post(response_1.url,  # noqa
                                      data,
                                      name=create_placeholdered_url_for_stats(response_1.url))  # noqa

        survey_id = [int(s) for s in response_1.url.split('/') if s.isdigit()][0]

        # do nothing for a while to give a chance for someone to fill it in
        for _i in range(0, 30):
            self.schedule_task(self._do_nothing)
        # now look at the report a few times  TODO: some different views
        self.schedule_task(self._view_report, args=[survey_id, ])
        self.schedule_task(self._view_report, args=[survey_id, ])
        self.schedule_task(self._view_report, args=[survey_id, ])
        self.schedule_task(self._view_report, args=[survey_id, ])

    def _view_report(self, survey_id):
        view_report_url = "/reports/{}/".format(survey_id)
        print(view_report_url)
        self.client.get(view_report_url,
                        name=create_placeholdered_url_for_stats(view_report_url))

    def _do_nothing(self):
        print('_do_nothing')

    @task
    def stop(self):
        print('stop')
        self.client.get('accounts/logout/')
        self.interrupt()


class WeThrive(TaskSet):
    tasks = {
        CreateSurvey: 1,
        CompleteSurvey: 10,
    }


class MyLocust(HttpLocust):
    host = os.getenv('TARGET_URL', "http://localhost")
    task_set = WeThrive
    min_wait = 2000
    max_wait = 5000


# print(create_team_member_excel_file(20))
