import conf
import mock
import unittest
import errors
from decimal import Decimal
from datetime import datetime
from tests.base import TestCaseApi, BaseTestCaseDB
from model import User, db, Option
from utils import mail
from api import validator


class TestOption(BaseTestCaseDB):

    def test_create(self):
        Option.create('test_key', 'test_value')
        with self.assertRaises(errors.OptionAlreadyExists):
            Option.create('test_key', 'test_value')

    def test_get_set(self):
        Option.set('test_key', 'test_value')
        val = Option.get('test_key')
        self.assertEqual(val, 'test_value')

        Option.set('test_key', 'test_value2')
        val = Option.get('test_key')
        self.assertEqual(val, 'test_value2')


class TestUserApi(TestCaseApi):
    def test_version(self):
        self.assertTrue(self.admin_client.version())

    def test_force_delete(self):
        User.new_user("test_test@test.ru", "test", "support", "$test_123123")
        db.session.commit()
        deleted = self.admin_client.delete("/api/0/_force_delete/",
                                           {"prefix": "$test", "tables": "user", "field": "name"}).json["deleted"]
        self.assertEqual(deleted["user"], 1)

        User.new_user("$test_test@test.ru", "testtest", "support")
        db.session.commit()
        deleted = self.admin_client.delete("/api/0/_force_delete/",
                                           {"prefix": "$test", "tables": "user"}).json["deleted"]
        self.assertEqual(deleted["user"], 1)

        deleted = self.admin_client.delete("/api/0/_force_delete/",
                                           {"prefix": "$test", "tables": "user"}).json["deleted"]
        self.assertEqual(deleted["user"], 0)

    def test_config_js(self):
        config = self.admin_client.get("/api/config.js")
        self.assertEqual(config.content_type, "application/x-javascript")

    def test_role(self):
        self.assertTrue(self.admin_client.get("/api/0/role").json["roles"])

    def test_country(self):
        self.assertTrue(self.admin_client.get("/api/0/country").json["countries"])

    def test_subscription(self):
        self.assertTrue(self.admin_client.get("/api/0/subscription").json["subscriptions"])

    def test_quotas_templates(self):
        self.assertTrue(self.admin_client.get("/api/0/quotas/templates").json["quotas_templates"])

    def test_language(self):
        languages = self.admin_client.get("/api/0/language").json["language_list"]
        self.assertTrue(languages)

        active_languages = self.admin_client.get("/api/0/language/active").json["language_list"]
        self.assertTrue(active_languages)
        self.assertLess(len(active_languages), len(languages))

        locales = self.admin_client.get("/api/0/locale/active").json["locale_list"]
        self.assertTrue(locales)

    def test_event_period(self):
        periods = self.admin_client.get("/api/0/event/auto_report/allowed_period/").json["periods"]
        self.assertTrue(periods)
        self.assertEqual(set(periods[0]["localized_name"].keys()), {"ru", "en"})
        with self.expect_error(errors.NotFound):
            self.admin_client.get("/api/0/event/auto_report2/allowed_period/")

    def test_health(self):
        self.assertTrue(self.admin_client.get("/api/0/health").json["health"])

    def test_test_email_sends(self):
        send_to = 'example@example.com'
        send_cc = ['one@example.com', 'two@example.com']
        send_cc_string = validator.EmailList.DEFAULT_STRING_DELIMITER.join(send_cc)
        subject = 'my custom subject'

        self.admin_client.post('/api/0/send_email/', {'send_to': send_to, 'send_cc': send_cc_string})
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, send_to)
        self.assertCountEqual(email.cc, send_cc)
        mail.outbox.clear()

        self.admin_client.post('/api/0/send_email/', {'send_to': send_to, 'subject': subject})
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.subject, subject)
        mail.outbox.clear()


class TestUtility(unittest.TestCase):
    def test_content_disposition(self):
        from utils import make_content_disposition

        filename = "test_тест.csv"
        self.assertEqual(make_content_disposition(filename),
                         "attachment;filename*=utf-8''test_%D1%82%D0%B5%D1%81%D1%82.csv")
        self.assertEqual(make_content_disposition(filename, "MSIE 5.0"),
                         "attachment;filename=test_%D1%82%D0%B5%D1%81%D1%82.csv")

        self.assertEqual(make_content_disposition(filename, "AppleWebKit"),
                         "attachment;filename=test_ÑÐµÑÑ.csv")


class TestTemplates(unittest.TestCase):
    def test_variables(self):
        variables = list(conf.message_template.variables)
        for template, data in conf.message_template.templates.items():
            template_variables = data.get('variables', [])
            if not template_variables:
                continue
            for variable in template_variables:
                if variable not in variables:
                    self.assertIsNone(variable,
                                      "Variable '%s' from template '%s' is not listed in 'variables' section" % (
                                          variable, template,))

    def test_formatter(self):
        from model.account.message_template import MessageTemplate
        template_data="""
            Test template Formatted:
                - balance - {{balance}}
                - current_date - {{current_date}}
                - current_time - {{current_time}}
                - current_datetime - {{current_datetime}}
            Simple:
                - user_name - {{user_name}}"""
        expected_text = """
            Test template Formatted:
                - balance - RUR15.00
                - current_date - Jul 5, 2015
                - current_time - 3:04:05 AM
                - current_datetime - Sunday, July 5, 2015 at 3:04:05 AM GMT+00:00
            Simple:
                - user_name - TEST_USER"""

        with mock.patch.object(MessageTemplate, 'get_template_data', return_value=template_data) as gtd:
            test_time = datetime(2015, 7, 5, 3, 4, 5)
            subject, body = MessageTemplate.get_rendered_message('NO VALUE HERE due to mock',
                                                                 language='en_US',
                                                                 balance={'money': Decimal('15.00'), 'currency': 'RUR'},
                                                                 current_date=test_time,
                                                                 current_time=test_time,
                                                                 current_datetime=test_time,
                                                                 user_name="TEST_USER")
            self.assertEqual(body, expected_text)
