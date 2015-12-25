import time
from api_tests.admin_backend import AdminBackendTestCase
from utils.tools import parse_backend_datetime


class NewsTestCase(AdminBackendTestCase):
    def search_news_in_list(self, news_list:list, news_id:int):
        for news in news_list:
            if news_id == news['news_id']:
                return news
        else:
            self.fail('News {} not found in news list'.format(news_id))


class TestNews(NewsTestCase):
    def setUp(self):
        super().setUp()
        self.default_news = self.create_news()

    def test_news_list(self):
        news_list = self.default_admin_client.news.list()
        self.search_news_in_list(news_list['items'], self.default_news['news_id'])

        news_list = self.default_admin_client.news.list(subject=self.default_news['subject'])
        self.search_news_in_list(news_list['items'], self.default_news['news_id'])

        news_list = self.default_admin_client.news.list(body=self.default_news['body'])
        self.search_news_in_list(news_list['items'], self.default_news['news_id'])

    def test_news_update(self):
        new_subject = self.create_name()
        old_subject = self.default_news['subject']
        self.default_news = self.default_admin_client.news.update(self.default_news['news_id'], subject=new_subject)
        self.assertEqual(new_subject, self.default_news['subject'])

        news_list = self.default_admin_client.news.list(subject=new_subject)
        news_info = self.search_news_in_list(news_list['items'], self.default_news['news_id'])
        self.assertEqual(new_subject, news_info['subject'])

        self.default_news = self.default_admin_client.news.update(self.default_news['news_id'], subject=old_subject)


class TestPublishingNews(NewsTestCase):
    def setUp(self):
        super().setUp()
        self.default_news = self.create_news()
        self.customer, _, self.customer_client = self.create_customer(create_default_tariff=True, with_client=True)

    def test_news_in_list(self):
        # not published not in list
        admin_news_list = self.default_admin_client.news.list()
        self.search_news_in_list(admin_news_list['items'], self.default_news['news_id'])

        news_list = self.customer_client.news.list()

        with self.assertRaises(self.failureException):
            self.search_news_in_list(news_list['items'], self.default_news['news_id'])

        # published in list
        self.default_admin_client.news.publish(self.default_news['news_id'], True)

        admin_news_list = self.default_admin_client.news.list(published=True)
        self.search_news_in_list(admin_news_list['items'], self.default_news['news_id'])

        news_list = self.customer_client.news.list()
        self.search_news_in_list(news_list['items'], self.default_news['news_id'])

        self.default_admin_client.news.publish(self.default_news['news_id'], False)

    def test_news_published_update(self):
        self.default_news = self.default_admin_client.news.publish(self.default_news['news_id'], True)
        old_published = parse_backend_datetime(self.default_news['published'].split('+')[0])

        time.sleep(1)

        self.default_news = self.default_admin_client.news.update(self.default_news['news_id'], self.default_news['subject'])
        new_published = parse_backend_datetime(self.default_news['published'].split('+')[0])

        self.assertGreater(new_published, old_published)


class TestDeletingNews(NewsTestCase):
    def setUp(self):
        super().setUp()
        self.default_news = self.create_news()
        self.customer, _, self.customer_client = self.create_customer(create_default_tariff=True, with_client=True)

    def test_deleted_news_not_in_list(self):
        self.default_admin_client.news.publish(self.default_news['news_id'], True)
        self.default_admin_client.news.delete(self.default_news['news_id'])

        news_list = self.customer_client.news.list()
        with self.assertRaises(self.failureException):
            self.search_news_in_list(news_list['items'], self.default_news['news_id'])


class TestDeletedNewsOperations(NewsTestCase):
    def setUp(self):
        super().setUp()
        self.default_news = self.create_news()
        self.default_admin_client.news.delete(self.default_news['news_id'])
        self.customer, _, self.customer_client = self.create_customer(create_default_tariff=True, with_client=True)

    def test_deleted_news_not_in_list(self):
        news_list = self.default_admin_client.news.list()

        with self.assertRaises(self.failureException):
            self.search_news_in_list(news_list['items'], self.default_news['news_id'])

        news_list = self.default_admin_client.news.list(visible=False)
        self.search_news_in_list(news_list['items'], self.default_news['news_id'])

    def test_cant_update_deleted_news(self):
        with self.assertRaisesHTTPError(409):
            self.default_admin_client.news.update(self.default_news['news_id'], subject=self.create_name('NewsSubject'))

        with self.assertRaisesHTTPError(409):
            self.default_admin_client.news.publish(self.default_news['news_id'], True)

        with self.assertRaisesHTTPError(409):
            self.default_admin_client.news.delete(self.default_news['news_id'])
