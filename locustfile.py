import os
from locust import HttpLocust, TaskSet, task, web
from testable_smtpd import SMTPD_PORT, SMTPD_HOSTNAME, get_last_message_for
from bs4 import BeautifulSoup
import uuid
import random
from slugify import slugify
import re

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
def smtp():
    return "<pre>EMAIL_HOST={}\nEMAIL_HOST_PASSWORD=\nEMAIL_HOST_USER=\nEMAIL_HOST_PORT={}</pre>".format(
        SMTPD_HOSTNAME,
        "",
        "",
        SMTPD_PORT
    )


@web.app.route("/env")
def env():
    return "<pre>{}</pre>".format("\n".join(["{} = \"{}\"".format(k, v) for (k, v) in os.environ.items()]))


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
        message = get_last_message_for(email)
        if message is not None:
            print('GOT MESSAGE!')
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
        data = {
            "csrfmiddlewaretoken": csrfmiddlewaretoken,
        }
        print(response_1.url)
        print(data)
        response_2 = self.client.post(response_1.url, data)
        response_2
        # print(response_2.content)

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
