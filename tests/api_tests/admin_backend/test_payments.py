import datetime
import json
import random
from api_tests.admin_backend import AdminBackendTestCase
import configs
from utils.tools import format_backend_datetime
import unittest


class CloudpaymentsTests(AdminBackendTestCase):
    ERROR_OK = 0
    ERROR_INVALID_INVOICE = 10
    ERROR_INVALID_AMOUNT = 11
    ERROR_COMMON = 13
    ERROR_OVERDUE = 20

    amount = 100

    @staticmethod
    def datetime_format(datetime_:datetime.datetime):
        return format_backend_datetime(datetime_, sep=' ')

    data_check_example = {
        'TransactionId': 0,
        'Amount': '0.00',
        'AccountId': 0,
        'Currency': 'RUB',
        'Email': 'example@example.com',
        'DateTime': format_backend_datetime(datetime.datetime.now(), sep=' '),
        'Status': 'Completed',
        'TestMode': False,
        'CardFirstSix': 123456,
        'CardLastFour': 1234,
        'CardType': 'Visa',
        'CardExpDate': '10/50',
    }

    @classmethod
    def payment_check(cls, **data):
        return cls.default_admin_client.payments.cloudpayments.check(configs.payments.cloudpayments.api_secret, **data)

    @classmethod
    def payment_pay(cls, **data):
        return cls.default_admin_client.payments.cloudpayments.pay(configs.payments.cloudpayments.api_secret, **data)

    @classmethod
    def generate_check_data(cls, amount:int, account_id, datetime_:datetime.datetime=None, email:str=None,
                            transaction_id:int=None, test_mode:bool=False, **kwargs):
        data = cls.data_check_example.copy()

        data['Amount'] = str(amount) + '.00'

        if transaction_id is None:
            data['TransactionId'] = random.randint(1, 10000)
        else:
            data['TransactionId'] = transaction_id

        if datetime_ is None:
            data['DateTime'] = cls.datetime_format(datetime.datetime.utcnow())
        else:
            data['DateTime'] = cls.datetime_format(datetime_)

        if email is not None:
            data['Email'] = email

        data['AccountId'] = account_id

        data['TestMode'] = test_mode
        data.update(kwargs)

        return data

    def test_successful_payment(self):
        customer_info, _, customer_client = self.create_customer(True, confirmed=True, go_prod=True, individual=True,
                                                                 make_full_prod=True, with_client=True,
                                                                 mailtrap_email=True)
        balance = int(float(customer_info['account']['RUB']['balance'])) + self.amount

        data = self.generate_check_data(self.amount, account_id=customer_info['customer_id'])
        status = self.payment_check(**data)['code']
        self.assertEqual(status, self.ERROR_OK)

        data['Data'] = json.dumps({
            'saveAsDefault': True
        })
        data['Token'] = 'Hello, wolrd!'

        status = self.payment_pay(**data)['code']
        self.assertEqual(status, self.ERROR_OK)

        customer_info = customer_client.customer.get()
        self.assertIn(str(balance), customer_info['account']['RUB']['balance'])

        cards = customer_client.customer.payments.get_cards()
        self.assertEqual(len(cards), 1)
        self.assertEqual(str(cards[0]['last_four']), str(data['CardLastFour']))

        customer_client.customer.payments.delete_card(cards[0]['card_id'])
        cards = customer_client.customer.payments.get_cards()
        self.assertEqual(len(cards), 0)

        self.search_email(r'сумма: {}.*?\(остаток на счете: {}.*?\)'.format(self.amount, balance))

    def test_double_payment(self):
        customer_info, _, customer_client = self.create_customer(True, confirmed=True, go_prod=True, individual=True, make_full_prod=True, with_client=True)
        balance = int(float(customer_info['account']['RUB']['balance'])) + self.amount

        data = self.generate_check_data(self.amount, account_id=customer_info['customer_id'])
        status = self.payment_check(**data)['code']
        self.assertEqual(status, self.ERROR_OK)

        data['Data'] = json.dumps({
            'saveAsDefault': True
        })

        status = self.payment_pay(**data)['code']
        self.assertEqual(status, self.ERROR_OK)

        status = self.payment_pay(**data)['code']
        self.assertEqual(status, self.ERROR_OK)

        customer_info = customer_client.customer.get()
        self.assertIn(str(balance), customer_info['account']['RUB']['balance'])

    def test_account_id_abcent(self):
        data = self.generate_check_data(self.amount, account_id=None)
        status = self.payment_check(**data)['code']
        self.assertEqual(status, self.ERROR_COMMON)

        status = self.payment_pay(**data)['code']
        self.assertEqual(status, self.ERROR_OK)

    def test_invalid_account_id(self):
        data = self.generate_check_data(self.amount, account_id=0)
        status = self.payment_check(**data)['code']
        self.assertEqual(status, self.ERROR_COMMON)

        status = self.payment_pay(**data)['code']
        self.assertEqual(status, self.ERROR_OK)

    def test_invalid_hmac(self):
        data = self.generate_check_data(self.amount, account_id=0)
        status = self.default_admin_client.payments.cloudpayments.check('124124', **data)['code']
        self.assertEqual(status, self.ERROR_COMMON)

        status = self.payment_pay(**data)['code']
        self.assertEqual(status, self.ERROR_OK)

    @unittest.skipIf(configs.payments.cloudpayments.allow_test_mode, 'TestMode is allowed')
    def test_test_mode(self):
        data = self.generate_check_data(self.amount, account_id=0, test_mode=True)
        status = self.payment_check(**data)['code']
        self.assertEqual(status, self.ERROR_COMMON)

        status = self.payment_pay(**data)['code']
        self.assertEqual(status, self.ERROR_OK)

    def test_invalid_status(self):
        data = self.generate_check_data(self.amount, account_id=0, Status='Authorized')
        status = self.payment_check(**data)['code']
        self.assertEqual(status, self.ERROR_COMMON)

        status = self.payment_pay(**data)['code']
        self.assertEqual(status, self.ERROR_OK)

    def test_invalid_amount(self):
        data = self.generate_check_data(-self.amount, account_id=0)
        status = self.payment_check(**data)['code']
        self.assertEqual(status, self.ERROR_COMMON)

        status = self.payment_pay(**data)['code']
        self.assertEqual(status, self.ERROR_OK)

    def test_invalid_currency(self):
        extract = lambda currency_list: {curr['code'] for curr in currency_list}

        all_currencies = extract(self.default_admin_client.currency.get())
        active_currencies = extract(self.default_admin_client.currency.get_active())
        inactive_currencies = all_currencies - active_currencies

        data = self.generate_check_data(self.amount, account_id=0, Currency=inactive_currencies.pop())
        status = self.payment_check(**data)['code']
        self.assertEqual(status, self.ERROR_COMMON)

        status = self.payment_pay(**data)['code']
        self.assertEqual(status, self.ERROR_OK)

    def test_customer_test_mode(self):
        customer_info, _ = self.create_customer(True)

        data = self.generate_check_data(self.amount, account_id=customer_info['customer_id'])
        status = self.payment_check(**data)['code']
        self.assertEqual(status, self.ERROR_COMMON)

        status = self.payment_pay(**data)['code']
        self.assertEqual(status, self.ERROR_OK)
