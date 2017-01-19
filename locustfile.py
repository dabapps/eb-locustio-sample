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
        # NOTE: It's the 2nd form on this page !?
        csrfmiddlewaretoken = forms[1].input['value']
        data = {  # FIXME: hardcoded to wrong persons team!!!
            "csrfmiddlewaretoken": csrfmiddlewaretoken,
            "survey_members-TOTAL_FORMS": "10",
            "survey_members-INITIAL_FORMS": "10",
            "survey_members-MIN_NUM_FORMS": "0",
            "survey_members-MAX_NUM_FORMS": "1000",
            "survey_members-0-member_added": "on",
            "survey_members-0-member_id": "10999",
            "survey_members-0-member_email": "boba.fett+afcd9153-aeac-4d09-b903-e1da8a2de408@example.com",
            "survey_members-0-member_display_name": "Boba Fett",
            "survey_members-1-member_added": "on",
            "survey_members-1-member_id": "10998",
            "survey_members-1-member_email": "boba.skywalker+073151b4-9eea-4675-835d-0996bfc0468b@example.com",
            "survey_members-1-member_display_name": "Boba Skywalker",
            "survey_members-2-member_added": "on",
            "survey_members-2-member_id": "11006",
            "survey_members-2-member_email": "chewy.skywalker+97a8e8f2-7033-462e-afcc-c1b0e9181ce5@example.com",
            "survey_members-2-member_display_name": "Chewy Skywalker",
            "survey_members-3-member_added": "on",
            "survey_members-3-member_id": "11005",
            "survey_members-3-member_email": "chewy.solo+777fe7c0-3354-425a-94af-e3d903128bf3@example.com",
            "survey_members-3-member_display_name": "Chewy Solo",
            "survey_members-4-member_added": "on",
            "survey_members-4-member_id": "11003",
            "survey_members-4-member_email": "chewy.solo+e41d6404-4c32-4b4b-a96b-5beb47d6f30f@example.com",
            "survey_members-4-member_display_name": "Chewy Solo",
            "survey_members-5-member_added": "on",
            "survey_members-5-member_id": "11004",
            "survey_members-5-member_email": "chewy.solo+e7bf8943-f362-424e-926a-ebf1bade560b@example.com",
            "survey_members-5-member_display_name": "Chewy Solo",
            "survey_members-6-member_added": "on",
            "survey_members-6-member_id": "11001",
            "survey_members-6-member_email": "han.fett+2600e775-4b12-4718-8017-2d2f2040f8bb@example.com",
            "survey_members-6-member_display_name": "Han Fett",
            "survey_members-7-member_added": "on",
            "survey_members-7-member_id": "11007",
            "survey_members-7-member_email": "han.hutt+ce92821f-e2df-495e-b2d3-f42e53e61ed1@example.com",
            "survey_members-7-member_display_name": "Han Hutt",
            "survey_members-8-member_added": "on",
            "survey_members-8-member_id": "11000",
            "survey_members-8-member_email": "leia.solo+b0672206-a76c-4148-bd80-1c73b8990bb6@example.com",
            "survey_members-8-member_display_name": "Leia Solo",
            "survey_members-9-member_added": "on",
            "survey_members-9-member_id": "11002",
            "survey_members-9-member_email": "luke.skywalker+f3bb4613-498e-4e20-b2eb-0d737f75271c@example.com",
            "survey_members-9-member_display_name": "Luke Skywalker",
        }
        print(data)
        response_2 = self.client.post(response_1.url, data)  # noqa
        preview_survey_url = response_2.url

        self.schedule_task(self._preview_survey, args=[preview_survey_url, ])

    def _preview_survey(self, preview_survey_url):
        response_1 = self.client.get(preview_survey_url)
        data = {
            # no csrf on this form
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
