import os
from locust import HttpLocust, TaskSet, task


class CreateSurvey(TaskSet):

    def on_start(self):
        print('CreateSurvey  - on_start')
        self.locust.summary()
        # create survey here?
        self.client.get("/")

    @task(1)
    def abandon_it(self):
        print('CreateSurvey - abandon_it')
        self.locust.summary()
        self.client.get("/")
        self.interrupt()

    @task(1)
    def send_it(self):
        print('CreateSurvey - send_it')
        self.locust.num_open_surveys += 1
        self.locust.summary()
        self.client.get("/")
        self.interrupt()

    @task(1)
    def send_it_and_something(self):
        print('CreateSurvey - send_it_and_something')
        self.locust.num_open_surveys += 1
        self.locust.summary()
        self.client.get("/")
        self.interrupt()


class ViewSurveyReport(TaskSet):

    def on_start(self):
        if self.locust.num_open_surveys <= 0:
            print("ViewSurveyReport - No point, no surveys!")
            self.interrupt()

    @task(10)
    def view_report_this_way(self):
        print('ViewSurveyReport - view_report_this_way')
        self.locust.summary()
        self.client.get("/")

    @task(10)
    def view_report_that_way(self):
        print('ViewSurveyReport - view_report_that_way')
        self.locust.summary()
        self.client.get("/")

    @task(1)
    def stop(self):
        print('ViewSurveyReport - stop')
        self.locust.summary()
        self.interrupt()


class RespondToSurvey(TaskSet):
    def on_start(self):
        if self.locust.num_open_surveys <= 0:
            print("RespondToSurvey - No point, no surveys!")
            self.interrupt()
        print('RespondToSurvey  - on_start')
        # Work out who to respond as.
        self.locust.summary()

    @task(1)
    def something(self):
        print('RespondToSurvey  - something')
        self.locust.summary()
        self.interrupt()


class WeThriveTaskSet(TaskSet):
    tasks = {
        CreateSurvey: 1,
        ViewSurveyReport: 5,
        RespondToSurvey: 10
    }

    def on_start(self):
        print('WeThriveTaskSet  - on_start')
        self.locust.summary()
        # sign up and sign in


class MyLocust(HttpLocust):
    host = os.getenv('TARGET_URL', "http://localhost")
    task_set = WeThriveTaskSet
    min_wait = 250
    max_wait = 500
    num_open_surveys = 0

    def summary(self):
        # print(self.num_open_surveys)
        pass
