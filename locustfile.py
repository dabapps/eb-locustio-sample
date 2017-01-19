import os
from locust import HttpLocust, TaskSet, task, web
from testable_smtpd import SMTPD_PORT, SMTPD_HOST, get_last_message_for
from bs4 import BeautifulSoup
import uuid
import random
from slugify import slugify
import re
import requests

FIRST_NAMES = ("Han", "Leia", "Chewy", "Luke", "Boba")
SECOND_NAMES = ("Solo", "Skywalker", "Fett", "Hutt")


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


@web.app.route("/smtp")
def www_smtp():
    return "<pre>EMAIL_HOST={}\nEMAIL_HOST_PASSWORD=\nEMAIL_HOST_USER=\nEMAIL_HOST_PORT={}</pre>".format(
        SMTPD_HOST,
        "",
        "",
        SMTPD_PORT
    )


@web.app.route("/env")
def www_env():
    return "<pre>{}</pre>".format(
        "\n".join(["{} = \"{}\"".format(k, v) for (k, v) in os.environ.items()])
    )


@web.app.route("/get_last_message_for/<email_address>")
def www_get_last_message_for(email_address):
    return get_last_message_for(email_address)


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
        request_1 = requests.get("http://{}:8000/get_last_message_for/{}".format(SMTPD_HOST, email))
        message = str(request_1.content)
        if message is not None:
            print('GOT MESSAGE!')
            # print(message)
            matches = re.search("(account/activate/[^\/]+/)", message, re.MULTILINE)
            if matches:
                finish_signup_url = matches.group(1)
                self.schedule_task(self._finish_signup, args=[name, email, finish_signup_url])
            else:
                raise Exception("Unable to extract activation link!")
        else:
            self.schedule_task(self._wait_for_signup_email, args=[name, email])

    def _finish_signup(self, name, email, finish_signup_url):
        print('_finish_signup {}'.format(finish_signup_url))
        response_1 = self.client.get(finish_signup_url, name="/account/activate/[id]/")
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
        response_2 = self.client.post(response_1.url, data)  # noqa
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

        self.schedule_task(self._create_team)

    def _create_team(self):
        response_1 = self.client.get("people/")
        soup = BeautifulSoup(response_1.content, 'html.parser')
        csrfmiddlewaretoken = soup.form.input['value']
        num_team_members_to_create = 10
        team_members_email_addresses_csv = "\n".join(["{},{}".format(*generate_random_email_and_name()) for x in range(0, num_team_members_to_create)])
        data = {
            "csrfmiddlewaretoken": csrfmiddlewaretoken,
            "email_addresses": team_members_email_addresses_csv,
            "verb": "Add",
        }
        print(data)
        response_2 = self.client.post('people/', data)  # noqa
        # print(response_2.content)

        self.schedule_task(self._create_survey)

    def _create_survey(self):
        self.client.get("surveys/")

        response_1 = self.client.get("surveys/create/")
        soup = BeautifulSoup(response_1.content, 'html.parser')
        csrfmiddlewaretoken = soup.form.input['value']
        data = {
            "csrfmiddlewaretoken": csrfmiddlewaretoken,
            "auto_close_date": "26/01/2017",    # FIXME: hardcoded date
            "name": "Survey Name",
            "company_name": "Company Name",
            "auto_start_date": "19/01/2017",    # FIXME: hardcoded date
            "start_time": "16:30",              # FIXME: hardcoded time
            "end_date_week": 1,
            "auto_nudge_enabled": "on",
        }
        print(data)
        response_2 = self.client.post('surveys/create/', data)  # noqa
        choose_team_to_send_survey_to_url = response_2.url

        self.schedule_task(self._choose_team_to_send_survey_to_url, args=[choose_team_to_send_survey_to_url, ])

    def _choose_team_to_send_survey_to_url(self, choose_team_to_send_survey_to_url):
        print(choose_team_to_send_survey_to_url)
        response_1 = self.client.get(choose_team_to_send_survey_to_url)
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
        response_2 = self.client.post(response_1.url, data)  # noqa
        preview_survey_url = response_2.url

        self.schedule_task(self._preview_survey, args=[preview_survey_url, ])

    def _preview_survey(self, preview_survey_url):
        response_1 = self.client.get(preview_survey_url)
        soup = BeautifulSoup(response_1.content, 'html.parser')
        csrfmiddlewaretoken = soup.form.input['value']
        data = {
            "csrfmiddlewaretoken": csrfmiddlewaretoken,
        }
        print(data)
        response_2 = self.client.post(response_1.url, data)  # noqa

    @task
    def stop(self):
        print('stop')
        self.client.get('accounts/logout/')
        self.interrupt()


class WeThrive(TaskSet):
    tasks = {
        CreateSurvey: 1,
        # RespondSurvey: 10,
        # ViewReports: 1,
    }


class MyLocust(HttpLocust):
    host = os.getenv('TARGET_URL', "http://localhost")
    task_set = WeThrive
    min_wait = 1000
    max_wait = 2000
