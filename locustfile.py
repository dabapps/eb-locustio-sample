import os
from locust import HttpLocust, TaskSet, task, web
import requests


@web.app.route("/smtp")
def smtp():
    return "<pre>EMAIL_HOST={}\nEMAIL_HOST_PASSWORD=\nEMAIL_HOST_USER=\nEMAIL_HOST_PORT=2525</pre>".format(
        requests.get("http://169.254.169.254/latest/meta-data/public-hostname").content,
        "",
        "",
        None
    )


@web.app.route("/env")
def env():
    return "<pre>{}</pre>".format("\n".join(["{} = \"{}\"".format(k, v) for (k, v) in os.environ.items()]))


class RespondSurvey(TaskSet):

    def on_start(self):
        print('RespondSurvey - on_start')
        # sign up or in

    @task
    def respond_quickly(self):
        print('respond_quickly')
        self.interrupt()

    @task
    def respond_slowly(self):
        print('respond_slowly')
        self.interrupt()


class CreateSurvey(TaskSet):

    def on_start(self):
        # sign up or in
        pass

    # @task(5)
    # def abandon_it(self):
    #     print('CreateSurvey - abandon_it')
    #     self.client.get("/")

    @task(1)
    def send_it(self):
        print('CreateSurvey - send_it')
        self.client.get("/")

        # This is no good because it's sequential!!
        self.schedule_task(RespondSurvey(self).run)
        self.schedule_task(RespondSurvey(self).run)
        self.schedule_task(RespondSurvey(self).run)
        self.schedule_task(RespondSurvey(self).run)
        self.schedule_task(RespondSurvey(self).run)

        # self.schedule_task(self.view_report, [21])
        # self.schedule_task(self.view_report, [22])
        # self.schedule_task(self.view_report, [23])
        # self.schedule_task(self.view_report, [24])
        # self.schedule_task(self.view_report, [25])

    # @task(1)
    # def send_it_and_something(self):
    #     print('CreateSurvey - send_it_and_something')
    #     self.client.get("/")

    def respond_to_survey(self, info):
        print('respond_to_survey {}'.format(info))

    def view_report(self, info):
        print('view_report {}'.format(info))


class WeThrive(TaskSet):
    tasks = {
        CreateSurvey: 1,
        RespondSurvey: 10,
        # ViewReports: 1,
    }


class MyLocust(HttpLocust):
    host = os.getenv('TARGET_URL', "http://localhost")
    task_set = WeThrive
    min_wait = 1000
    max_wait = 2000
