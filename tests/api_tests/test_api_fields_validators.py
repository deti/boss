import datetime
import unittest.case
from requests import HTTPError
import entities
from utils.base import BaseTestCase


class _CheckValidatorContext(unittest.case._AssertRaisesContext):
    def __init__(self, field_name, func, test_case):
        super().__init__(HTTPError, test_case)
        self.field_name = field_name
        self.func = func

    def __exit__(self, exc_type, exc_val, exc_tb):
        message = 'Client method: {}\nApi url: {}\nField: {}\n'
        if exc_type is HTTPError:
            url = exc_val.request.url
            method = exc_val.request.method
            status_code = exc_val.response.status_code
            message = message.format(self.func.__qualname__, method + ' ' + url, self.field_name)
            if status_code >= 500:
                self._raiseFailure(message + 'Failed with status code {}. Expected 400.'.format(status_code))
            elif status_code != 400:
                self._raiseFailure('Raised not {} status code.Expected 400.\n{}'.format(status_code, exc_val.response.text))
            return True
        elif exc_type is None:
            message = message.format(self.func.__qualname__, self.func.__doc__.strip(), self.field_name)
            self._raiseFailure(message + 'HTTPError not raised.')
            return True
        return super().__exit__(exc_type, exc_val, exc_tb)


class ApiFieldsTestsBase(BaseTestCase):
    big_string_length = 4096
    big_string_template = '_123456789'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin_client = cls.get_admin_client()

    def generate_big_string(self):
        test_prefix = self.get_test_prefix()
        return test_prefix + self.big_string_template * (
        (self.big_string_length - len(test_prefix)) // len(self.big_string_template))

    def check_api_method(self, func: callable, fields: list, kwargs: dict, big_string: str=None):
        for field in fields:
            func_kwargs = kwargs.copy()
            string = self.generate_big_string() if big_string is None else big_string
            if '.' in field:
                first, second = field.split('.')
                func_kwargs[first][second] = string
            else:
                func_kwargs[field] = string
            with _CheckValidatorContext(field, func, self):
                func(**func_kwargs)


class NewsFieldsTest(ApiFieldsTestsBase):
    def test_news_creation(self):
        self.addCleanupDelete('news')
        info = entities.News(self).generate()
        self.check_api_method(self.admin_client.news.create, ['subject'], info)

    def test_news_update(self):
        news = self.create_news()
        info = entities.News(self).generate()
        info.update(dict(news_id=news['news_id']))
        self.check_api_method(self.admin_client.news.update, ['subject'], info)


class TariffFieldsTest(ApiFieldsTestsBase):
#    def test_tariff_creation_description(self):
#        self._update_current_func_force_delete(tariff='localized_name')
#        info = entities.Tariff(self).generate()
#        self.check_api_method(self.admin_client.tariff.create, ['description'], info)

    def test_tariff_creation_localized_name(self):
        self.addCleanupDelete('tariff')
        info = entities.Tariff(self).generate()
        localized_long = entities.Entity(self).localized_name(True)
        localized_long.update({'en': self.generate_big_string()})
        self.check_api_method(self.admin_client.tariff.create, ['localized_name'], info, localized_long)

#    def test_tariff_update_description(self):
#        tariff = self.create_tariff()
#        self.check_api_method(self.admin_client.tariff.update, ['description'], {'tariff_id': tariff['tariff_id']})


class ServiceFieldsTest(ApiFieldsTestsBase):
    def test_service_create_localized_name(self):
        self.addCleanupDelete('service')
        info = entities.Service(self).generate()
        localized_long = entities.Entity(self).localized_name(True)
        localized_long.update({'en': self.generate_big_string()})
        self.check_api_method(self.admin_client.service.create, ['localized_name'], info, localized_long)


class UserFieldsTest(ApiFieldsTestsBase):
    def test_user_creation(self):
        self.addCleanupDelete('user')
        info = entities.AdminCredentials(self).generate()
        self.check_api_method(self.admin_client.user.create, ['password', 'name'], info)

    def test_user_update_self(self):
        user_info, _, user_client = self.create_user(with_client=True)
        info = {'name': entities.AdminCredentials(self).basic_name(),
                'password': entities.AdminCredentials(self).generate_password()}
        self.check_api_method(user_client.user.update, ['password', 'name'], info)

    def test_user_update_admin(self):
        user_info, _, user_client = self.create_user(with_client=True)
        info = {'name': entities.AdminCredentials(self).basic_name(),
                'password': entities.AdminCredentials(self).generate_password(),
                'user_id': user_info['user_id']}
        self.check_api_method(user_client.user.update, ['password', 'name'], info)

    def test_user_creation_email(self):
        self.addCleanupDelete('user')
        info = entities.AdminCredentials(self).generate()
        self.check_api_method(self.admin_client.user.create, ['email'], info,
                              self.generate_big_string() + '@example.com')


class CustomerFieldsTest(ApiFieldsTestsBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cabinet_client = cls.get_cabinet_client()

    def test_customer_creation_email(self):
        self.addCleanupDelete('customer')
        info = entities.CustomerCredentials(self).generate()
        self.check_api_method(self.cabinet_client.customer.create, ['email'], info,
                              self.generate_big_string() + '@example.com')

    def test_customer_creation(self):
        self.addCleanupDelete('customer')
        info = entities.CustomerCredentials(self).generate()
        self.check_api_method(self.cabinet_client.customer.create,
                              ['password', 'detailed_info.name', 'detailed_info.city',
                               'detailed_info.address', 'detailed_info.country', 'detailed_info.telephone'], info)

#    def test_customer_update_by_admin(self):
#        self.get_or_create_default_tariff()
#        customer_info = self.create_customer()[0]
#        info = {'customer_id': customer_info['customer_id'], 'detailed_info': {'name': customer_info['detailed_info']['name']}}
#        self.check_api_method(self.admin_client.customer.update, ['comment'], info)
#
#    def test_customer_delete_by_admin(self):
#        self.get_or_create_default_tariff()
#        customer_info = self.create_customer()[0]
#        info = {'customer_id': customer_info['customer_id']}
#        self.check_api_method(self.admin_client.customer.delete, ['comment'], info)
#
#    def test_customer_block_by_admin(self):
#        self.get_or_create_default_tariff()
#        customer_info = self.create_customer()[0]
#        info = {'customer_id': customer_info['customer_id'], 'blocked': True}
#        self.check_api_method(self.admin_client.customer.block, ['message'], info)
#
#    def test_customer_deferred_update(self):
#        self.get_or_create_default_tariff()
#        customer_info = self.create_customer()[0]
#        tariff = self.create_tariff(immutable=True)
#        date = self.make_datetime(datetime.datetime.today() + datetime.timedelta(days=1))
#        info = {'customer_id': customer_info['customer_id'], 'tariff': tariff['tariff_id'], 'date': date}
#        try:
#            self.check_api_method(self.admin_client.customer.deferred.update, ['comment'], info)
#        finally:
#            self.admin_client.customer.deferred.force(customer_info['customer_id'])
#
#    def test_customer_balance(self):
#        self.get_or_create_default_tariff()
#        customer_info = self.create_customer()[0]
#        info = {'customer_id': customer_info['customer_id'], 'amount': 124}
#        self.check_api_method(self.admin_client.customer.update_balance, ['comment'], info)