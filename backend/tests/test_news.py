import errors
from arrow import utcnow
from tests.base import BaseTestCaseDB, TestCaseApi
from model import News, db, Tariff, Customer
from utils.mail import outbox


class TestNews(BaseTestCaseDB):
    def test_news_create(self):
        News.create_news('news subject', 'news body')
        db.session.flush()


class TestNewsApi(TestCaseApi):
    test_news = {'subject': 'test subject', 'body': "test body"}
    news_to_compare = dict(deleted=None, published=None, **test_news)

    def generate_user(self, role):
        return {"email": "%s@boss.ru" % role, "password": "asd{}%".format(role.capitalize()),
                "name": role.capitalize(), "role": role}

    def create(self, role):
        if role != "admin":
            new_user = self.generate_user(role)
            self.admin_client.user.create(**new_user)
            self.admin_client.auth(new_user['email'], new_user['password'])
        else:
            self.admin_client.auth(self.email, self.password)

        if role != "support":
            news = self.admin_client.news.create(**self.test_news)
            news.pop('news_id')
            self.assertEqual(news, self.news_to_compare)

            # create with wrong subject
            with self.expect_error(errors.BadRequest):
                self.admin_client.news.create(body='test body',
                                              subject="111111111sjhbjxhvkjhvkjhgvkjhgvjhvjhvjh"
                                                      "vjlhvjhvljhvljhxbkmzlkmlsjndkhsbjchblmzl")
        else:
            self.expect_error(errors.UserInvalidRole)

    def test_create(self):
        roles = ['admin', 'account', 'manager', 'support']
        for role in roles:
            self.create(role)

    def create_news(self):
        news_ids = []
        for i in range(4):
            news = self.admin_client.news.create(**self.test_news)
            news_ids.append(news['news_id'])

        self.admin_client.news.publish(news_ids[0], publish=True)
        self.admin_client.news.delete(news_ids[0])

        self.admin_client.news.publish(news_ids[1], publish=True)

        self.admin_client.news.delete(news_ids[2])

    def test_get(self):
        with self.expect_error(errors.Unauthorized):
            self.cabinet_client.get("/lk_api/0/news/", auth_required=False)

        self.create_news()

        news_list = self.admin_client.news.list()
        self.assertEqual(len(news_list['items']), 2)
        self.assertEqual(news_list['items'][0]['news_id'], 2)

        news_list = self.admin_client.news.list(visible=False)
        self.assertEqual(len(news_list['items']), 4)

        news_list = self.admin_client.news.list(visible=False, published=True)
        self.assertEqual(len(news_list['items']), 2)

        # check filtering by creation date
        hour_ago = utcnow().replace(hours=-1).datetime
        in_hour = utcnow().replace(hours=+1).datetime

        filtered_news = self.admin_client.news.list(visible=False, deleted_before=in_hour)
        self.assertEqual(len(filtered_news['items']), 2)

        filtered_news = self.admin_client.news.list(visible=False, deleted_before=hour_ago)
        self.assertEqual(len(filtered_news['items']), 0)

        filtered_news = self.admin_client.news.list(visible=False, deleted_after=in_hour)
        self.assertEqual(len(filtered_news['items']), 0)

        filtered_news = self.admin_client.news.list(visible=False, deleted_after=hour_ago)
        self.assertEqual(len(filtered_news['items']), 2)

        filtered_news = self.admin_client.news.list(visible=False, published_before=in_hour)
        self.assertEqual(len(filtered_news['items']), 2)

        filtered_news = self.admin_client.news.list(visible=False, published_before=hour_ago)
        self.assertEqual(len(filtered_news['items']), 0)

        filtered_news = self.admin_client.news.list(visible=False, published_after=in_hour)
        self.assertEqual(len(filtered_news['items']), 0)

        filtered_news = self.admin_client.news.list(visible=False, published_after=hour_ago)
        self.assertEqual(len(filtered_news['items']), 2)

        with self.expect_error(errors.BadRequest):
            self.admin_client.news.list(sort='+published')

        self.tariff = Tariff.create_tariff(self.localized_name("Tariff for customers"), "tariff!!!", "RUB", None)
        db.session.commit()
        password = "simplecustomer"
        email = "email@email.ru"
        self.cabinet_client.customer.create(email=email, password=password)
        self.cabinet_client.auth(email, password)
        self.cabinet_client.get("/lk_api/0/news/")

    def test_update(self):
        news_id = self.admin_client.news.create(**self.test_news)['news_id']

        # update subject
        news = self.admin_client.news.update(news_id, subject="new test subject")
        self.assertEqual(news['subject'], "new test subject")

        # update body
        news = self.admin_client.news.update(news_id, body="new test body")
        self.assertEqual(news['body'], "new test body")

        # update with wrong subject
        with self.expect_error(errors.BadRequest):
            self.admin_client.news.update(news_id,
                                          subject="111111111sjhbjxhvkjhvkjhgvkjhgvjhvjhvjh"
                                                  "vjlhvjhvljhvljhxbkmzlkmlsjndkhsbjchblmzl")

        # update deleted news
        self.admin_client.news.delete(news_id)
        with self.expect_error(errors.RemovedNews):
            self.admin_client.news.update(news_id, body="new test body")

    def test_publish(self):
        Tariff.create_tariff(self.localized_name("tariff_for_balance"), "tariff!!!", "rub", None)
        customer_id = Customer.new_customer("email@email.ru", "123qwe", self.admin_user.user_id).customer_id
        db.session.commit()
        customer = Customer.get_by_id(customer_id)
        news_id = self.admin_client.news.create(**self.test_news)['news_id']

        # check publish
        news = self.admin_client.news.publish(news_id, publish=True)
        self.assertTrue(news['published'])
        self.assertEqual(outbox[0].to, [customer.email])
        self.assertIn(self.test_news['subject'], outbox[0].subject)

        news_id = self.admin_client.news.create(subject='$test_subject', body='test_body')['news_id']
        self.admin_client.news.publish(news_id, publish=True)
        self.assertEqual(len(outbox), 1)

        # check unpublish
        news = self.admin_client.news.publish(news_id, publish=False)
        self.assertFalse(news['published'])
        self.assertEqual(len(outbox), 1)

        # check publish deleted news
        self.admin_client.news.delete(news_id)
        with self.expect_error(errors.RemovedNews):
            self.admin_client.news.publish(news_id, publish=True)

    def test_delete(self):
        news_id = self.admin_client.news.create(**self.test_news)['news_id']
        self.admin_client.news.delete(news_id)
        with self.expect_error(errors.RemovedNews):
            self.admin_client.news.delete(news_id)

    def test_force_delete(self):
        self.admin_client.news.create(subject='$test subject', body="test body")
        deleted = self.admin_client.delete("/api/0/_force_delete/",
                                           {"tables": "news", "prefix": "$test"}).json["deleted"]
        self.assertEqual(deleted["news"], 1)


