import mock
import arrow
import errors
import re
import conf
import uuid

from fitter.aggregation.timelabel import TimeLabel
from tests.base import BaseTestCaseDB, TestCaseApi, ResponseError, Deferred
from model import (Customer, db, Subscription, SubscriptionSwitch, Tariff, Quote, Tenant, ServiceUsage, TimeState,
                   PromoCode, display, CustomerCard)
from datetime import timedelta, datetime
from utils.mail import outbox
from decimal import Decimal
from random import randint
from mock import patch, MagicMock
from os_interfaces.openstack_wrapper import openstack


class TestCustomer(BaseTestCaseDB):

    def test_customer_create(self):
        Tariff.create_tariff(self.localized_name("tariff1"), "tariff!!!", "rub", None)
        new_customer_info = {"name": "test customer", "birthday": "1999-01-01", "country": "Russia", "city": "Moscow",
                             "address": "Kreml, 1a", "telephone": "8(999)999 99 99"}
        Customer.new_customer("email@email.ru", "123qwe", None, new_customer_info)
        db.session.flush()
        with self.assertRaises(errors.CustomerAlreadyExists):
            Customer.new_customer("email@email.ru", "123qwe", None, new_customer_info)
            db.session.flush()

    def test_balance(self):
        Tariff.create_tariff(self.localized_name("tariff_for_balance"), "tariff!!!", "rub", None)
        customer = Customer.new_customer("email@email.ru", "123qwe", self.admin_user.user_id)

        customer.modify_balance(Decimal("3.33"), "RUB", self.admin_user.user_id, "test balance 1")
        self.assertEqual(len(outbox), 1)
        self.assertEqual(outbox[0].subject, '%s: Уведомление о пополнении счета' % conf.provider.cloud_name)

        cust = Customer.get_by_id(customer.customer_id)
        rub = cust.account_dict()["RUB"]
        self.assertEqual(rub["balance"], Decimal("3.33"))
        self.assertEqual(rub["withdraw"], Decimal("0"))
        self.assertEqual(rub["current"], Decimal("3.33"))

        history = list(cust.get_account_history())
        self.assertEqual(len(history), 2)

        customer.modify_balance(Decimal("7.47"), "eur", self.admin_user.user_id, "eur increase")

        cust = Customer.get_by_id(customer.customer_id)
        eur = cust.account_dict()["EUR"]
        self.assertEqual(eur["balance"], Decimal("7.47"))

        customer.modify_balance(Decimal("-7.47"), "eur", self.admin_user.user_id, "eur decrease")
        self.assertEqual(len(outbox), 3)
        self.assertEqual(outbox[2].subject, '%s: Уведомление о списании со счета' % conf.provider.cloud_name)

        cust = Customer.get_by_id(customer.customer_id)
        eur = cust.account_dict()["EUR"]
        self.assertEqual(eur["balance"], Decimal("0"))

        history = list(cust.get_account_history())
        self.assertEqual(len(history), 5)

        customer2 = Customer.new_customer("email2@email.ru", "123qwe", self.admin_user.user_id)
        history2 = list(customer2.get_account_history())
        self.assertEqual(len(history2), 1)

        history = list(cust.get_account_history())
        self.assertEqual(len(history), 5)

        # test blocking
        customer3 = Customer.new_customer("email3@email.ru", "123qwe", self.admin_user.user_id)
        customer3.modify_balance(Decimal("-3.33"), "rub", self.admin_user.user_id, "test blocking rub")
        cust = Customer.get_by_id(customer3.customer_id)
        self.assertTrue(cust.blocked)
        self.assertEqual(len(outbox), 5)
        self.assertIn('по причине исчерпания средств на вашем Счете', outbox[-1].body)

        customer4 = Customer.new_customer("email4@email.ru", "123qwe", self.admin_user.user_id)
        customer4.modify_balance(Decimal("-3.33"), "eur", self.admin_user.user_id, "test blocking eur")
        cust = Customer.get_by_id(customer4.customer_id)
        self.assertFalse(cust.blocked)

        customer4.withdraw(Decimal(1), 'eur')
        cust = Customer.get_by_id(customer4.customer_id)
        self.assertFalse(cust.blocked)

        customer5 = Customer.new_customer("email5@email.ru", "123qwe", self.admin_user.user_id)
        customer5.withdraw(Decimal(1), 'rub')
        cust = Customer.get_by_id(customer5.customer_id)
        self.assertTrue(cust.blocked)

        customer5.modify_balance(Decimal(1000), 'rub', None, None)
        self.assertFalse(cust.blocked)

    def test_balance_history(self):
        from model import AccountHistory
        Tariff.create_tariff(self.localized_name("tariff_for_balance"), "tariff!!!", "rub", None)
        customer = Customer.new_customer("email@email.ru", "123qwe", self.admin_user.user_id)

        customer.modify_balance(Decimal("3.33"), "rub", self.admin_user.user_id, "test balance history")
        history = list(customer.get_account_history())
        self.assertEqual(len(history), 2)

        after = arrow.utcnow().replace(weeks=+1).datetime
        before = arrow.utcnow().replace(weeks=-1).datetime

        history = list(customer.get_account_history(after=after))
        self.assertEqual(len(history), 0)

        history = list(customer.get_account_history(before=before))
        self.assertEqual(len(history), 0)

        before = after = arrow.utcnow().replace(minutes=+1).datetime
        account = customer.get_account('rub')
        account.history.append(AccountHistory.create(customer, account.account_id, None, 'test history',
                                                     '3.33', date=arrow.utcnow().replace(days=+1).datetime))

        history = list(customer.get_account_history(after=after))
        self.assertEqual(len(history), 1)

        history = list(customer.get_account_history(before=before))
        self.assertEqual(len(history), 2)

    def test_blocking(self):
        Tariff.create_tariff(self.localized_name("tariff_for_balance"), "tariff!!!", "rub", None)
        customer = Customer.new_customer("email@email.ru", "123qwe", self.admin_user.user_id)
        customer.confirm_email()
        # this is because customer after confirm_email is detached from session
        customer = Customer.query.filter(Customer.email == "email@email.ru").first()
        customer.make_production(None, 'Test blocking')
        customer.block(True, None, 'Test blocking')
        self.assertTrue(customer.blocked)
        self.assertEqual(openstack.update_user.call_count, 1)
        expected_call_args = [
            mock.call(customer.os_user_id, enabled=False)
        ]
        self.assertEqual(openstack.update_user.call_args_list, expected_call_args)
        time_state = TimeState.query.\
            filter(TimeState.name == 'block_customer', TimeState.customer_id == customer.customer_id).first()
        self.assertTrue(time_state)
        customer.block(False, None, 'Test unblocking')
        self.assertFalse(customer.blocked)
        self.assertEqual(openstack.update_user.call_count, 2)
        expected_call_args = mock.call(customer.os_user_id, enabled=True)
        self.assertEqual(openstack.update_user.call_args_list[-1], expected_call_args)
        time_state = TimeState.query.\
            filter(TimeState.name == 'block_customer', TimeState.customer_id == customer.customer_id).first()
        self.assertFalse(time_state)

        customer = Customer.new_customer("email1@email.ru", "123qwe", self.admin_user.user_id)
        customer.confirm_email()
        # this is because customer after confirm_email is detached from session
        customer = Customer.query.filter(Customer.email == "email1@email.ru").first()
        customer.block(True, None, 'Test blocking')
        self.assertTrue(customer.blocked)
        self.assertEqual(openstack.update_user.call_count, 3)
        expected_call_args = mock.call(customer.os_user_id, enabled=False)
        self.assertEqual(openstack.update_user.call_args_list[-1], expected_call_args)
        time_state = TimeState.query.\
            filter(TimeState.name == 'block_customer', TimeState.customer_id == customer.customer_id).first()
        self.assertFalse(time_state)

        customer = Customer.new_customer("email2@email.ru", "123qwe", self.admin_user.user_id)
        db.session.commit()
        customer.block(True, None, 'Test blocking')
        self.assertTrue(customer.blocked)
        self.assertEqual(openstack.update_user.call_count, 3)
        time_state = TimeState.query.\
            filter(TimeState.name == 'block_customer', TimeState.customer_id == customer.customer_id).first()
        self.assertFalse(time_state)

    def test_blocking_notification(self):
        from task.notifications import check_customers_for_balance
        from model.account.customer import Customer

        def create_customer(admin_id, email=None, name=None):
            uid = uuid.uuid4().hex  # random uuid hex string
            if not email:
                email = "%s@email.com" % uid
            if not name:
                name = "name-%s" % uid
            customer = Customer.new_customer(email, "123qwe", admin_id)
            customer.update_os_credentials("tenant_id_%s" % email,
                                           "%s_tenant" % name,
                                           "os_user_%s" % email,
                                           "os_user_%s" % email,
                                           "123qwe")
            return customer

        services = [{"service_id": "storage.image", "price": "1.0"},
                    {"service_id": "storage.volume", "price": "1.0"},
                    {"service_id": "storage.disk", "price": "1.0"},]
        Tariff.create_tariff(self.localized_name("tariff_for_balance"), "tariff!!!", "rub", services=services)

        finish = arrow.utcnow().datetime
        start = finish - timedelta(hours=24)

        # Boundary notification
        customer1 = create_customer(self.admin_user.user_id, "email1@email.com", "Customer - 1")
        customer1.modify_balance(Decimal("7000.0"), "rub", self.admin_user.user_id, "test balance 1")
        Customer.fake_usage(customer1, start, finish, "storage.disk", uuid.uuid4().hex, 10*conf.GIGA)
        Customer.fake_usage(customer1, start, finish, "storage.image", uuid.uuid4().hex, 13*conf.GIGA)
        Customer.fake_usage(customer1, start, finish, "storage.volume", uuid.uuid4().hex, 18*conf.GIGA)

        customer2 = create_customer(self.admin_user.user_id, "email2@email.com", "Customer - 2")
        customer2.modify_balance(Decimal("7000.0"), "rub", self.admin_user.user_id, "test balance 2")
        Customer.fake_usage(customer2, start, finish, "storage.disk", uuid.uuid4().hex, 30*conf.GIGA)
        Customer.fake_usage(customer2, start, finish, "storage.image", uuid.uuid4().hex, 60*conf.GIGA)

        # No notification
        customer3 = create_customer(self.admin_user.user_id, "email3@email.com", "Customer - 3")
        customer3.modify_balance(Decimal("7000.0"), "rub", self.admin_user.user_id, "test balance 3")
        Customer.fake_usage(customer3, start, finish, "storage.disk", uuid.uuid4().hex, 35*conf.GIGA)
        db.session.commit()

        # Check message sent
        outbox_len_before = len(outbox)
        check_customers_for_balance()
        self.assertEqual(outbox_len_before+2, len(outbox))

        # Check notification date is changing
        start = finish
        finish = finish + timedelta(hours=24)
        with mock.patch("arrow.utcnow", return_value=arrow.utcnow() + timedelta(hours=25)),\
             mock.patch("model.account.account.utcnow", return_value=arrow.utcnow() + timedelta(hours=24)):
            customer1.modify_balance(Decimal("-200.0"), "rub", self.admin_user.user_id, "test balance 4")
            customer2.modify_balance(Decimal("-200.0"), "rub", self.admin_user.user_id, "test balance 5")
            customer3.modify_balance(Decimal("-200.0"), "rub", self.admin_user.user_id, "test balance 6")

            Customer.fake_usage(customer1, start, finish, "storage.disk", uuid.uuid4().hex, 10*conf.GIGA)
            Customer.fake_usage(customer1, start, finish, "storage.image", uuid.uuid4().hex, 13*conf.GIGA)
            Customer.fake_usage(customer1, start, finish, "storage.volume", uuid.uuid4().hex, 18*conf.GIGA)

            Customer.fake_usage(customer2, start, finish, "storage.disk", uuid.uuid4().hex, 30*conf.GIGA)
            Customer.fake_usage(customer2, start, finish, "storage.image", uuid.uuid4().hex, 60*conf.GIGA)

            Customer.fake_usage(customer3, start, finish, "storage.disk", uuid.uuid4().hex, 40*conf.GIGA)

            from model.account.message_template import MessageTemplate
            template_data = """{{block_date}}"""
            with mock.patch.object(MessageTemplate, 'get_template_data', return_value=template_data):
                from model.account.message_template import Formatters
                from model import MessageTemplate

                outbox_len_before = len(outbox)
                check_customers_for_balance()
                self.assertEqual(outbox_len_before+3, len(outbox))
                formatters = MessageTemplate.get_formatters()

                expected_call_args = [
                    ('email1@email.com', 4, customer1),  # Block after 4 days
                    ('email2@email.com', 1, customer2),  # Block after 1 days
                    ('email3@email.com', 5, customer3),  # Block after 4 days
                ]
                for index, m in enumerate(outbox[-3:]):
                    self.assertEqual(expected_call_args[index][0], m.to)
                    date = arrow.utcnow()+timedelta(days=expected_call_args[index][1])
                    date_value = Formatters.format(formatters['block_date'],
                                                   expected_call_args[index][2].locale_language(),
                                                   date.datetime)
                    self.assertEqual(m.body, date_value)

    def test_delete_hdd_notification(self):
        customer_email = "customer@email.com"

        services = [{"service_id": "storage.image", "price": "1.0"}]
        Tariff.create_tariff(self.localized_name("tariff_for_balance"), "tariff!!!", "rub", services=services)

        customer = Customer.new_customer(customer_email, "123qwe", self.admin_user.user_id)
        customer.update_os_credentials("tenant_id_%s" % customer_email,
                                       "%s_tenant" % customer_email,
                                       "os_user_%s" % customer_email,
                                       "os_user_%s" % customer_email,
                                       "123qwe")
        customer.modify_balance(Decimal("10.0"), "rub", self.admin_user.user_id, "test balance 1")

        start = arrow.utcnow() - timedelta(days=10)
        finish = start + timedelta(days=1)

        with mock.patch("arrow.utcnow", return_value=start),\
                mock.patch("model.account.account.utcnow", return_value=start),\
                mock.patch("model.account.customer_history.utcnow", return_value=start):
            Customer.fake_usage(customer, start.datetime, finish.datetime, "storage.image", uuid.uuid4().hex, 1000*conf.GIGA)

        outbox_len_before = len(outbox)
        from task.notifications import notify_managers_about_hdd
        notify_managers_about_hdd(customer.customer_id)
        self.assertEqual(outbox_len_before+1, len(outbox))
        self.assertEqual(outbox[-1].to, conf.customer.manager.email)

    def test_withdraw_date(self):
        from model import ScheduledTask

        Tariff.create_tariff(self.localized_name("tariff1"), "tariff!!!", "rub", None)
        customer = Customer.new_customer("email@email.ru", "123qwe", self.admin_user.user_id, withdraw_period="month")

        customer.update({'withdraw_period': 'week'})
        task = ScheduledTask.get_by_customer(customer.customer_id, Customer.AUTO_REPORT_TASK)
        freq1 = task.frequency

        customer.update({'withdraw_period': 'quarter'})

        task = ScheduledTask.get_by_customer(customer.customer_id, Customer.AUTO_REPORT_TASK)
        freq2 = task.frequency
        self.assertNotEqual(freq1, freq2)

    def test_auto_report(self):
        from task.customer import auto_report

        services = [{"service_id": "storage.disk", "price": Decimal("12.34")}]
        tariff = Tariff.create_tariff(self.localized_name("tariff1"), "tariff!!!", "rub", services=services)
        tariff.mark_immutable()
        tariff.make_default()
        customer = Customer.new_customer("email@email.ru", "123qwe", self.admin_user.user_id, withdraw_period="month")
        tenant = Tenant.create("fake tenant_id", "fake tenant")
        db.session.add(tenant)
        db.session.flush()
        customer.os_tenant_id = tenant.tenant_id
        customer.tariff_id = tariff.tariff_id
        customer_id = customer.customer_id

        self.assertEqual(Customer.auto_withdraw_query().all(), [])

        now = arrow.utcnow().datetime
        future = now + timedelta(days=33)
        self.assertEqual(len(Customer.auto_withdraw_query(now=future).all()), 1)

        self.assertEqual(len(Customer.auto_withdraw_query(email_prefix="xxxx", now=future).all()), 0)
        self.assertEqual(len(Customer.auto_withdraw_query(email_prefix="email", now=future).all()), 1)

        time_label = TimeLabel(now - timedelta(hours=2))
        start, finish = time_label.datetime_range()
        service_usage = ServiceUsage(customer.os_tenant_id, "storage.disk", time_label,
                                     "auto_report_test", customer.tariff,
                                     354 * conf.GIGA, start, finish, resource_name="disk_disk")
        total_cost = customer.calculate_usage_cost([service_usage])
        self.assertEqual(total_cost, Decimal(354) * Decimal("12.34"))
        customer.withdraw(total_cost)
        db.session.add(service_usage)
        db.session.commit()

        auto_report(future)
        db.session.close()

        customer = Customer.get_by_id(customer_id)
        rub = customer.account_dict()["RUB"]
        self.assertEqual(rub["withdraw"], Decimal(0))
        self.assertEqual(rub["current"], -total_cost)
        self.assertEqual(rub["balance"], -total_cost)

    def test_period_is_over(self):
        from model import TimeMachine, TimeState
        tariff = Tariff.create_tariff(self.localized_name("tariff1"), "tariff!!!", "rub")
        tariff.mark_immutable()
        tariff.make_default()

        customer = Customer.new_customer("email@email.ru", "123qwe", self.admin_user.user_id,
                                         withdraw_period="month")
        customer.confirm_email()
        TimeMachine.check(now=arrow.utcnow().datetime + timedelta(days=10))
        customer = Customer.get_by_id(customer.customer_id)
        self.assertTrue(customer.blocked)
        TimeMachine.check(now=arrow.utcnow().datetime + timedelta(days=20))

    @mock.patch("conf.promocodes")
    def test_promocode(self, conf_promocodes):
        conf_promocodes.promo_registration_only = True
        today = arrow.utcnow().datetime
        conf_promocodes.codes = {
            'valid_code': today + timedelta(days=10),
            'expired': today,
        }

        Tariff.create_tariff(self.localized_name("tariff_for_balance"), "tariff!!!", "rub", None)
        customer = Customer.new_customer("email@email.ru", "123qwe", self.admin_user.user_id, promo_code="test_code")
        customer_id = customer.customer_id

        promocode = PromoCode.get_by_customer_id(customer_id)
        self.assertEqual(display(promocode), [{'value': 'test_code'}])

        Customer.delete_by_prefix('email')

        promocode = PromoCode.get_by_customer_id(customer_id)
        self.assertEqual(display(promocode), [])


class TestSubscription(BaseTestCaseDB):
    def test_subscription_create(self):
        Tariff.create_tariff(self.localized_name("tariff1"), "tariff!!!", "rub", None)
        customer = Customer.new_customer("email@email.ru", "123qwe", None)
        db.session.flush()
        Subscription.new_subscription("news", "customer@boss.ru", customer.customer_id)
        db.session.flush()
        with self.assertRaises(errors.SubscriptionAlreadyExists):
            Subscription.new_subscription("news", "customer@boss.ru", customer.customer_id)
        db.session.flush()


class TestSubscriptionSwitch(BaseTestCaseDB):
    def test_subscription_switch_create(self):
        Tariff.create_tariff(self.localized_name("tariff1"), "tariff!!!", "rub", None)
        customer = Customer.new_customer("email@email.ru", "123qwe", None)
        db.session.flush()
        with self.assertRaises(errors.SubscriptionSwitchAlreadyExists):
            SubscriptionSwitch.new_switch(True, "news", customer.customer_id)
        db.session.flush()


class TestQuota(BaseTestCaseDB):
    def test_quota_create(self):
        Tariff.create_tariff(self.localized_name("tariff1"), "tariff!!!", "rub", None)
        customer = Customer.new_customer("email@email.ru", "123qwe", None)
        name = "testmaxImageMeta"
        value = 5
        db.session.flush()
        Quote.new_quota(customer_id=customer.customer_id, name=name, value=value)
        db.session.flush()
        with self.assertRaises(errors.QuotaAlreadyExist):
            Quote.new_quota(customer_id=customer.customer_id, name=name, value=value)
        db.session.flush()


class TestCustomerApi(TestCaseApi):
    new_customer = {"email": "email@email.ru", "customer_type": "private",
                    "detailed_info": {"name": "test customer", "birthday": "1999-01-01", "country": "Russia",
                                      "city": "Moscow", "address": "Kreml, 1a", "telephone": "8(999)999 99 99"}}

    change_customer = {"email": "new+email@email.ru", "password": "asd_Customer%",
                       "detailed_info": {"name": "New name", "birthday": "19700101", "country": "USA",
                                         "city": "New-York", "address": "Manhatten 5b",
                                         "telephone": "89123456789"}}

    simple_new_customer = {"email": "email@email.ru"}

    def setUp(self):
        super().setUp()
        self.tariff = Tariff.create_tariff(self.localized_name("Tariff for customers"), "tariff!!!", "rub", None)
        db.session.commit()

    def test_simple_customer_create(self):
        password = "simplecustomer"
        self.cabinet_client.customer.create(password=password, **self.simple_new_customer)

        self.cabinet_client.auth(self.simple_new_customer["email"], password)
        self.cabinet_client.customer.get("me")

    def test_create_customer_without_password(self):
        from utils.mail import outbox
        self.admin_client.customer.create(email="customer_without_password@example.com")
        self.assertEqual(len(outbox), 1)
        confirm_token = re.findall(r"/confirmation/([^\s]+)\s?", outbox[0].body)[0]

        password_token = self.cabinet_client.customer.confirm_email(confirm_token)

        with self.expect_error(errors.Unauthorized):
            self.cabinet_client.auth("customer_without_password@example.com", "123456789000")

        self.cabinet_client.customer.reset_password(password_token, "1234567890")

        with self.expect_error(errors.Unauthorized):
            self.cabinet_client.auth("customer_without_password@example.com", "123456789000")

        self.cabinet_client.auth("customer_without_password@example.com", "1234567890")

    @patch('os_interfaces.openstack_wrapper.openstack.attach_subnet_to_router', MagicMock())
    def test_customer_signup(self):
        password = "customercustomer"
        res = self.cabinet_client.customer.create(password=password, withdraw_period='week', promo_code="bad_code", **self.new_customer)
        res.pop("customer_id")
        res.pop("created")
        res.pop("tariff_id")
        res.pop("withdraw_date")
        res.pop("balance_limit")
        res.pop("os_tenant_id")
        res.pop("os_user_id")
        res["detailed_info"].pop("passport_series_number")
        res["detailed_info"].pop("passport_issued_by")
        res["detailed_info"].pop("passport_issued_date")
        self.assertDictEqual(res, dict(deleted=None, email_confirmed=False, currency="RUB",
                                       blocked=False, customer_mode="test", withdraw_period="week",
                                       locale="ru_ru", os_username=None, promo_code=[],
                                       account={"RUB": {"balance": "0.00", "current": "0.00", "withdraw": "0.00"}},
                                       os_dashboard=conf.customer.default_openstack_dashboard,
                                       **self.new_customer))

        self.assertEqual(len(outbox), 1)
        confirm_token = re.findall(r"/confirmation/([^\s]+)\s?", outbox[0].body)[0]
        self.cabinet_client.customer.confirm_email(confirm_token)

        with self.expect_error(errors.EmailConfirmationTokenInvalid):
            self.cabinet_client.customer.confirm_email(confirm_token)

        self.cabinet_client.auth(self.new_customer["email"], password)
        cust = self.cabinet_client.customer.get("me")
        self.assertTrue(cust["email_confirmed"])
        self.assertTrue(cust["os_tenant_id"])
        self.assertTrue(cust["os_user_id"])

        self.cabinet_client.customer.request_confirm_email()
        self.assertEqual(len(outbox), 3)
        confirm_token = re.findall(r"/confirmation/([^\s]+)\s?", outbox[2].body)[0]
        self.cabinet_client.customer.confirm_email(confirm_token)

        subs = self.cabinet_client.get("/lk_api/0/customer/me/subscribe").json["subscribe"]
        for name in conf.subscription:
            if name in conf.customer.automatic_subscriptions:
                self.assertEqual(subs[name]["email"], [self.new_customer["email"]])
                self.assertTrue(subs[name]["enable"])
            else:
                self.assertFalse(subs[name]["email"])
                self.assertFalse(subs[name]["enable"])

        quota = self.cabinet_client.customer.quota("me").get()
        quota = self.prepare_quota_for_assertion(quota)
        self.assertEqual(conf.template.test_customer, quota)

        with self.expect_error(errors.CustomerAlreadyExists):
            self.cabinet_client.customer.create(password="asdCustomer%", **self.new_customer)

        self.admin_client.customer.recreate_tenant(cust["customer_id"])

        self.admin_client.customer.request_confirm_email(cust["customer_id"])

    def test_create_by_user(self):
        password = "simplecustomer"
        customer = self.admin_client.customer.create(password=password, email="email0@email.ru", make_prod=False)
        self.assertEqual(customer['customer_mode'], 'test')
        self.assertEqual(customer['withdraw_period'], 'week')
        quota = self.admin_client.customer.quota(customer['customer_id']).get()
        quota = self.prepare_quota_for_assertion(quota)
        self.assertEqual(conf.template.test_customer, quota)

        customer = self.admin_client.customer.create(password=password, withdraw_period='week', email='1@email.ru')
        self.assertEqual(customer['withdraw_period'], 'week')

        prod_new_customer = self.new_customer.copy()
        prod_new_customer["detailed_info"] = self.new_customer["detailed_info"].copy()
        prod_new_customer["detailed_info"].update({"passport_series_number": "1234 567 890",
                                                   "passport_issued_by": "UFMS Russia",
                                                   "passport_issued_date": "2013-01-01"})
        customer = self.admin_client.customer.create(password=password, make_prod=True, **prod_new_customer)
        self.assertEqual(customer['customer_mode'], 'production')
        quota = self.admin_client.customer.quota(customer['customer_id']).get()
        quota = self.prepare_quota_for_assertion(quota)
        self.assertEqual(conf.template.customer, quota)

    def test_success_login(self):
        self.cabinet_client.customer.create(password="asdCustomer%", **self.new_customer)
        res = self.cabinet_client.auth("email@email.ru", "asdCustomer%")
        self.assertEqual(res, {})

        res = self.cabinet_client.auth("email@email.ru", "asdCustomer%", return_customer_info=True)

        res.pop("customer_id")
        res.pop("created")
        res.pop("tariff_id")
        res.pop("withdraw_period")
        res.pop("withdraw_date")
        res.pop("balance_limit")
        res.pop("os_tenant_id")
        res.pop("os_user_id")
        res["detailed_info"].pop("passport_series_number")
        res["detailed_info"].pop("passport_issued_by")
        res["detailed_info"].pop("passport_issued_date")
        self.assertDictEqual(res, dict(deleted=None, email_confirmed=False, currency="RUB", blocked=False,
                                       customer_mode="test", locale="ru_ru", promo_code=[],
                                       account={"RUB": {"balance": "0.00", "current": "0.00", "withdraw": "0.00"}},
                                       os_username=None, os_dashboard=conf.customer.default_openstack_dashboard,
                                       **self.new_customer))

    def test_failed_login(self):
        # unknown customer
        with self.expect_error(errors.Unauthorized):
            self.cabinet_client.auth(email="unknown@email.ru", password="unknown")
        # incorrect password
        self.cabinet_client.customer.create(password="asdCustomer%", **self.new_customer)
        with self.expect_error(errors.Unauthorized):
            self.admin_client.auth(email=self.new_customer['email'], password="xzzzzz")

    def test_logout(self):
        self.cabinet_client.customer.create(password="asdCustomer%", **self.new_customer)
        res = self.cabinet_client.auth("email@email.ru", "asdCustomer%")
        self.cabinet_client.logout()
        with self.expect_error(errors.Unauthorized):
            self.cabinet_client.get("/lk_api/0/customer/me", auth_required=False)

    def verify_customer_update(self, customer_id, client):
        password = "asdCustomer%"
        with self.expect_error(errors.NothingForUpdate):
            client.customer.update(customer_id)

        # update password
        client.customer.update(customer_id, password=self.change_customer['password'])
        with self.expect_error(errors.Unauthorized):
            client.auth(email=self.new_customer['email'], password=password)

        #update customer type
        res = client.customer.update(customer_id, customer_type='entity')
        self.assertEqual(res['customer_type'], 'entity')

        client.customer.update(customer_id, customer_type='private')

        with self.expect_error(errors.BadParameter):
            client.customer.update(customer_id, password="pass")

        change_customer_info = self.change_customer["detailed_info"]
        # update birthday
        res = client.customer.update(customer_id, detailed_info={"birthday": change_customer_info['birthday']})
        self.assertEqual(res["detailed_info"]["birthday"], "1970-01-01")

        res = client.customer.update(customer_id, detailed_info={"birthday": "1970-01-02"})
        self.assertEqual(res["detailed_info"]["birthday"], "1970-01-02")

        with self.expect_error(errors.BadParameter):
            client.customer.update(customer_id, detailed_info={"birthday": "197001011536"})

        # update country
        res = client.customer.update(customer_id, detailed_info={"country": change_customer_info['country']})
        self.assertEqual(res["detailed_info"]["country"], change_customer_info['country'])

        # update city
        res = client.customer.update(customer_id, detailed_info={"city": None})
        self.assertEqual(res["detailed_info"]["city"], None)

        res = client.customer.update(customer_id, detailed_info={"city": change_customer_info['city']})
        self.assertEqual(res["detailed_info"]["city"], change_customer_info['city'])

        # update address
        res = client.customer.update(customer_id, detailed_info={"address": change_customer_info['address']})
        self.assertEqual(res["detailed_info"]["address"], change_customer_info['address'])

        # update telephone
        res = client.customer.update(customer_id, detailed_info={"telephone": change_customer_info['telephone']})
        self.assertEqual(res["detailed_info"]["telephone"], change_customer_info['telephone'])

        # update name
        res = client.customer.update(customer_id, detailed_info={"name": self.change_customer["detailed_info"]["name"]})
        self.assertEqual(res["detailed_info"]["name"], self.change_customer["detailed_info"]["name"])

    def test_self_change_customer(self):
        password = "asdCustomer%"
        self.cabinet_client.customer.create(password=password, **self.new_customer)
        self.cabinet_client.auth(email=self.new_customer['email'], password=password)

        with self.expect_error(errors.NothingForUpdate):
            self.cabinet_client.customer.update("me", email=self.change_customer['email'])

        self.verify_customer_update("me", self.cabinet_client)

        with self.expect_error(errors.BadRequest):
            self.cabinet_client.customer.update("me", locale="enasdfasdf")

        customer_info = self.cabinet_client.customer.update("me", locale="en")
        self.assertEqual(customer_info["locale"], "en")

    def generate_user(self, role):
        return {"email": "%s@boss.ru" % role, "password": "asd{}%".format(role.capitalize()),
                "name": role.capitalize(), "role": role}

    def update_support(self, customer_id):
        for key, value in self.change_customer.items():
            with self.expect_error(errors.UserInvalidRole):
                self.admin_client.customer.update(customer_id, **{key: value})

    def update_by_user(self, role):
        password = "asdCustomer%"
        customer_id = self.cabinet_client.customer.create(password=password, **self.new_customer)['customer_id']

        self.admin_client.customer.update(customer_id, password="updated_password", comment="update password")

        if role != "admin":
            new_user = self.generate_user(role)
            self.admin_client.user.create(**new_user)
            self.admin_client.auth(new_user['email'], new_user['password'])
        else:
            self.admin_client.auth(self.email, self.password)

        if role != "support":
            # update email
            self.admin_client.customer.update(customer_id, email=self.change_customer['email'])
            with self.expect_error(errors.Unauthorized):
                self.admin_client.auth(email=self.new_customer['email'], password=password)

            self.verify_customer_update(customer_id, self.admin_client)

            cust_info = self.admin_client.customer.block(customer_id)
            self.assertTrue(cust_info["blocked"])
            self.assertNotIn('due to insufficient funds', outbox[-1].body)

            self.admin_client.customer.update_balance(customer_id, 1000, 'test')
            self.assertTrue(cust_info["blocked"])

            cust_info = self.admin_client.customer.block(customer_id, blocked=False)
            self.assertFalse(cust_info["blocked"])

            # update email confirmed
            self.assertFalse(cust_info["email_confirmed"])
            res = self.admin_client.customer.update(customer_id, confirm_email=True)
            self.assertTrue(res["email_confirmed"])

            customer = Customer.get_by_id(customer_id)
            customer.delete_by_prefix('new')
        else:
            self.update_support(customer_id)

    def test_update_openstack_dashboard(self):
        customer_id = self.cabinet_client.customer.create(password='password', **self.new_customer)['customer_id']

        # Check get Customer info
        admin_res = self.admin_client.customer.get(customer_id)
        cabinet_res = self.cabinet_client.customer.get('me')
        self.assertEqual(admin_res['os_dashboard'], conf.customer.default_openstack_dashboard)
        self.assertEqual(cabinet_res['os_dashboard'], conf.customer.default_openstack_dashboard)

        # Check change dashboard to "skyline"
        with self.expect_error(errors.BadRequest):
            self.cabinet_client.customer.update("me", os_dashboard="skyline", comment="change OS dashboard")
        cabinet_res = self.cabinet_client.customer.get('me')
        self.assertEqual(cabinet_res['os_dashboard'], conf.customer.default_openstack_dashboard)

        admin_res = self.admin_client.customer.update(customer_id, os_dashboard="skyline", comment="change OS dashboard")
        self.assertEqual(admin_res['os_dashboard'], "skyline")

        # Check change dashboard to "both"
        with self.expect_error(errors.BadRequest):
            self.cabinet_client.customer.update("me", os_dashboard="both", comment="change OS dashboard")
        cabinet_res = self.cabinet_client.customer.get('me')
        self.assertEqual(cabinet_res['os_dashboard'], "skyline")

        admin_res = self.admin_client.customer.update(customer_id, os_dashboard="both", comment="change OS dashboard")
        self.assertEqual(admin_res['os_dashboard'], "both")

        # Check change dashboard to Invalid value
        with self.expect_error(errors.BadParameter):
            self.cabinet_client.customer.update("me", os_dashboard="invalid", comment="change OS dashboard")
        cabinet_res = self.cabinet_client.customer.get('me')
        self.assertEqual(cabinet_res['os_dashboard'], "both")

        with self.expect_error(errors.BadParameter):
            self.admin_client.customer.update(customer_id, os_dashboard="invalid", comment="change OS dashboard")
        cabinet_res = self.cabinet_client.customer.get('me')
        self.assertEqual(cabinet_res['os_dashboard'], "both")

    def test_update_by_user(self):
        roles = ['admin', 'account', 'manager', 'support']
        for role in roles:
            self.update_by_user(role)

    def test_balance_limit_update_by_user(self):
        password = "asdCustomer%"
        customer_id = self.cabinet_client.customer.create(password=password, **self.new_customer)['customer_id']
        self.admin_client.auth(self.email, self.password)

        with self.expect_error(errors.BadParameter):
            self.admin_client.customer.update(customer_id, balance_limit="wrong value")
        new_balance_limit = "-15"
        res = self.admin_client.customer.update(customer_id, balance_limit=new_balance_limit)
        self.assertEqual(Decimal(res["balance_limit"]), Decimal(new_balance_limit))

    def test_tariff_change(self):
        password = "newcustomer"
        customer = self.cabinet_client.customer.create(password=password, **self.new_customer)
        customer_tariff = self.cabinet_client.customer.get_tariff("me")
        self.assertEqual(len(customer_tariff["services"]), 0)
        self.assertNotIn("description", customer_tariff)
        self.assertNotIn("parent_id", customer_tariff)
        Customer.get_by_id(customer["customer_id"]).confirm_email()

        customer_tariff_by_admin = self.admin_client.customer.get_tariff(customer["customer_id"])
        self.assertIn("description", customer_tariff_by_admin)
        self.assertIn("parent_id", customer_tariff_by_admin)
        self.assertIn("default", customer_tariff_by_admin)
        self.assertIn("created", customer_tariff_by_admin)
        self.assertIn("deleted", customer_tariff_by_admin)

        tariff_data = {
            'localized_name': {
                'en': 'some name',
                'ru': 'Какое то имя'
            },
            'description': 'Tariff description',
            'currency': 'RUB',
            'services': [
                {
                    "service_id": self.service_small_id,
                    "price": "12.23"
                },
                {
                    "service_id": self.service_medium_id,
                    "price": "21.32"
                }
            ]
        }
        new_tariff = self.admin_client.tariff.create(as_json=True, **tariff_data)
        with self.expect_error(errors.AssignMutableTariff):
            self.admin_client.customer.update(customer["customer_id"], tariff=new_tariff["tariff_id"])

        self.admin_client.tariff.immutable(new_tariff["tariff_id"])
        self.admin_client.customer.update(customer["customer_id"], tariff=new_tariff["tariff_id"])
        self.assertTrue(openstack.change_flavors.called)

        new_customer_tariff = self.cabinet_client.customer.get_tariff("me")
        self.assertEqual(len(new_customer_tariff["services"]), 2)

        c = self.admin_client.customer.get(customer["customer_id"])
        self.assertTrue(c)

        history = self.admin_client.customer.history(customer["customer_id"])
        self.assertEqual(len(history), 4)

        history = self.admin_client.customer.history(customer["customer_id"], after=datetime(2010, 1, 1))
        self.assertEqual(len(history), 4)

        history = self.admin_client.customer.history(customer["customer_id"],
                                                     before=(arrow.utcnow() + timedelta(hours=1)).datetime)
        self.assertEqual(len(history), 4)

        history = self.admin_client.customer.history(customer["customer_id"], after=datetime(2010, 1, 1),
                                                     before=(arrow.utcnow() + timedelta(hours=1)).datetime)
        self.assertEqual(len(history), 4)

    def test_subscription_info(self):
        password = "asdCustomer%"
        self.cabinet_client.customer.create(password=password, **self.new_customer)
        self.cabinet_client.auth(email=self.new_customer['email'], password=password)

        self.assertTrue(self.cabinet_client.customer.get_subscription("me"))

    def test_subscription_update(self):
        password = "asdCustomer%"
        self.cabinet_client.customer.create(password=password, **self.new_customer)
        self.cabinet_client.auth(email=self.new_customer['email'], password=password)

        body = {"subscribe": {
                "news": {"enable": False, "email": ["a@a.ru", "b@b.ru"]},
                "billing": {"enable": False, "email": ["a@a.ru", "b@b.ru"]},
                "status": {"enable": True, "email": ["c@c.ru"]}}}

        res = self.cabinet_client.put("/lk_api/0/customer/me/subscribe", params=body, as_json=True).json['subscribe']
        for name, data in body["subscribe"].items():
            self.assertEqual(data, res[name])

    def test_deferred(self):
        password = "deferreddeferred"
        customer = self.cabinet_client.customer.create(password=password, **self.new_customer)

        deferred = self.admin_client.customer.deferred(customer["customer_id"])
        self.assertIsNone(deferred.get(), None)

        tariff_data = {
            'localized_name': {
                'en': 'some name',
                'ru': 'Какое то имя'
            },
            'description': 'Tariff description',
            'currency': 'RUB',
            'services': [
                {
                    "service_id": self.service_small_id,
                    "price": "12.23"
                },
                {
                    "service_id": self.service_medium_id,
                    "price": "21.32"
                }
            ]
        }
        new_tariff = self.admin_client.tariff.create(as_json=True, **tariff_data)
        now = arrow.utcnow().datetime

        with self.expect_error(errors.AssignMutableTariff):
            deferred.update(new_tariff["tariff_id"], now + timedelta(seconds=2))

        self.admin_client.tariff.immutable(new_tariff["tariff_id"])
        customer_deferred = deferred.update(new_tariff["tariff_id"], now + timedelta(seconds=2))

        self.assertTrue(customer_deferred)

        customer_deferred = deferred.update(new_tariff["tariff_id"], now + timedelta(seconds=12))
        self.assertTrue(customer_deferred)

        customer_tariff = self.admin_client.customer.get_tariff(customer["customer_id"])["tariff_id"]
        deferred.force()
        self.assertIsNone(deferred.get())
        new_customer_tariff = self.admin_client.customer.get_tariff(customer["customer_id"])["tariff_id"]
        self.assertNotEqual(customer_tariff, new_customer_tariff)

        deferred.update(new_tariff["tariff_id"], now + timedelta(seconds=20))
        deferred.delete()
        self.assertIsNone(deferred.get())

        customer_deferred = deferred.update(new_tariff["tariff_id"], now + timedelta(seconds=5))
        self.assertTrue(customer_deferred)

        from model import Deferred

        count = Deferred.process_pending_deferred_changes(name_prefix="qqqqq", time_now=now + timedelta(seconds=100))
        self.assertEqual(count, 0)
        count = Deferred.process_pending_deferred_changes(time_now=now + timedelta(seconds=100))
        self.assertEqual(count, 1)

        customer_deferred = deferred.update(new_tariff["tariff_id"], now + timedelta(seconds=15))
        self.assertTrue(customer_deferred)

        count = Deferred.process_pending_deferred_changes(name_prefix="test", time_now=now + timedelta(seconds=100))
        self.assertEqual(count, 1)

        count = Deferred.process_pending_deferred_changes(name_prefix="test", time_now=now + timedelta(seconds=100))
        self.assertEqual(count, 0)

    def test_subscription_info_by_user(self):
        password = "asdCustomer%"
        customer_id = self.cabinet_client.customer.create(password=password, **self.new_customer)['customer_id']
        self.admin_client.auth(self.email, self.password)

        self.assertTrue(self.admin_client.customer.get_subscription(customer_id))

    def test_subscription_update_by_user(self):
        password = "asdCustomer%"
        customer_id = self.cabinet_client.customer.create(password=password, **self.new_customer)['customer_id']
        self.admin_client.auth(self.email, self.password)

        body = {"subscribe": {
                "news": {"enable": False, "email": ["a@a.ru", "b@b.ru"]},
                "billing": {"enable": False, "email": ["a@a.ru", "b@b.ru"]},
                "status": {"enable": True, "email": ["c@c.ru"]}}}

        res = self.admin_client.put("/api/0/customer/%s/subscribe" % customer_id, params=body,
                                    as_json=True).json['subscribe']
        for name, data in body["subscribe"].items():
            self.assertEqual(data, res[name])

    def test_subscription_failed_update(self):
        password = "asdCustomer%"
        self.cabinet_client.customer.create(password=password, **self.new_customer)
        self.cabinet_client.auth(email=self.new_customer['email'], password=password)

        # not dict
        body = {"subscribe": [{
                "news": {"enable": False, "email": ["a@a.ru", "b@b.ru"]},
                "billing": {"enable": False, "email": ["a@a.ru", "b@b.ru"]},
                "status": {"enable": True, "email": ["c@c.ru"]}}]}

        with self.expect_error(errors.InvalidSubscription):
            self.cabinet_client.put("/lk_api/0/customer/me/subscribe", params=body, as_json=True)

        # wrong key
        body = {"subscribe": {
                "news": {"fdxcgf": False, "email": ["a@a.ru", "b@b.ru"]},
                "billing": {"enable": False, "email": ["a@a.ru", "b@b.ru"]},
                "status": {"enable": True, "email": ["c@c.ru"]}}}

        with self.expect_error(errors.InvalidSubscription):
            self.cabinet_client.put("/lk_api/0/customer/me/subscribe", params=body, as_json=True)

        # wrong key
        body = {"subscribe": {
                "news": {"enable": False, "em": ["a@a.ru", "b@b.ru"]},
                "billing": {"enable": False, "email": ["a@a.ru", "b@b.ru"]},
                "status": {"enable": True, "email": ["c@c.ru"]}}}

        with self.expect_error(errors.InvalidSubscription):
            self.cabinet_client.put("/lk_api/0/customer/me/subscribe", params=body, as_json=True)

        # wrong email
        body = {"subscribe": {
                "news": {"enable": False, "email": ["a@a", "b@b.ru"]},
                "billing": {"enable": False, "email": ["a@a.ru", "b@b.ru"]},
                "status": {"enable": True, "email": ["c@c.ru"]}}}

        with self.expect_error(errors.InvalidSubscription):
            self.cabinet_client.put("/lk_api/0/customer/me/subscribe", params=body, as_json=True)

        # wrong bool
        body = {"subscribe": {
                "news": {"enable": "Fals", "email": "a@a.ru"},
                "billing": {"enable": False, "email": ["a@a.ru", "b@b.ru"]},
                "status": {"enable": True, "email": ["c@c.ru"]}}}

        with self.expect_error(errors.InvalidSubscription):
            self.cabinet_client.put("/lk_api/0/customer/me/subscribe", params=body, as_json=True)

        # wrong subscription name
        body = {"subscribe": {
                "news1": {"enable": False, "email": ["a@a.ru", "b@b.ru"]},
                "billing": {"enable": False, "email": ["a@a.ru", "b@b.ru"]},
                "status": {"enable": True, "email": ["c@c.ru"]}}}

        with self.expect_error(errors.InvalidSubscription):
            self.cabinet_client.put("/lk_api/0/customer/me/subscribe", params=body, as_json=True)

    def test_support(self):
        password = "asdCustomer%"

        msg = {'subject': 'test subject', 'body': 'test body'}

        self.cabinet_client.customer.create(password=password, **self.new_customer)
        self.cabinet_client.auth(email=self.new_customer['email'], password=password)

        self.cabinet_client.post("/lk_api/0/customer/support", params=msg)
        self.assertEqual(len(outbox), 2)

        self.cabinet_client.post("/lk_api/0/customer/support", params=dict(copy='test@boss.ru, test1@boss.ru', **msg))
        self.assertEqual(len(outbox), 3)

    def prepare_quota_for_assertion(self, quota):
        prepared_quota = {limit["limit_id"]: limit["value"] for limit in quota}

        return prepared_quota

    def quota_change(self, role):
        password = "asdCustomer%"
        customer_id = self.cabinet_client.customer.create(password=password, **self.new_customer)['customer_id']
        if role != "admin":
            new_user = self.generate_user(role)
            self.admin_client.user.create(**new_user)
            self.admin_client.auth(new_user['email'], new_user['password'])
        else:
            self.admin_client.auth(self.email, self.password)

        for name in Quote.display_fields:
            if role != "support":
                value = randint(0, 2**32)
                quota = self.admin_client.customer.quota(customer_id).update(limits={name: value})
                quota = self.prepare_quota_for_assertion(quota)
                self.assertEqual(value, quota[name])
            else:
                with self.assertRaises(errors.UserInvalidRole):
                    value = randint(0, 2 ** 32)
                    self.admin_client.customer.quota(customer_id).update(limits={name: value})

    def test_quota_change(self):
        roles = ['admin', 'account', 'manager', 'support']
        for role in roles:
            yield self.quota_change(role)

    def test_failed_quota_change(self):
        password = "asdCustomer%"
        customer_id = self.cabinet_client.customer.create(password=password, **self.new_customer)['customer_id']
        self.admin_client.auth(self.email, self.password)

        # invalid value
        with self.expect_error(errors.BadRequest):
            self.admin_client.customer.quota(customer_id).update(limits={"maxImageMeta": "!"})

        # invalid name
        with self.expect_error(errors.BadRequest):
            self.admin_client.customer.quota(customer_id).update(limits={"maxImageMeta1": "5"})

    def test_get_quota_by_user(self):
        password = "asdCustomer%"
        customer_id = self.cabinet_client.customer.create(password=password, **self.new_customer)['customer_id']
        self.admin_client.auth(self.email, self.password)
        quota = self.admin_client.customer.quota(customer_id).get()
        quota = self.prepare_quota_for_assertion(quota)
        self.assertEqual(conf.template.test_customer, quota)

    def test_change_quota_template(self):
        password = "asdCustomer%"
        customer_id = self.cabinet_client.customer.create(password=password, **self.new_customer)['customer_id']
        self.admin_client.auth(self.email, self.password)
        quota = self.admin_client.customer.quota(customer_id).change_template({'template': 'customer'})
        quota = self.prepare_quota_for_assertion(quota)
        self.assertEqual(conf.template.customer, quota)

    def verify_production_state(self, customer, balance, balance_limit=Decimal("0.0")):
        self.assertEqual(customer["customer_mode"], "production")
        self.assertEqual(Decimal(customer["account"]["RUB"]["balance"]), balance)
        self.assertEqual(Decimal(customer["balance_limit"]), balance_limit)
        quota = self.admin_client.customer.quota(customer["customer_id"]).get()
        quota = self.prepare_quota_for_assertion(quota)
        self.assertEqual(conf.template.customer, quota)

    @patch('task.customer.clean_up_customer_service_usage', MagicMock())
    def test_blocked_customer_make_prod_by_admin(self):
        password = "asdCustomer%"
        self.admin_client.auth(self.email, self.password)
        customer_id = self.admin_client.customer.create(password=password, **self.new_customer)["customer_id"]
        customer = Customer.get_by_id(customer_id)
        customer.modify_balance(Decimal("-3.33"), "rub", self.admin_user.user_id, '')


        self.admin_client.customer.update(customer_id, detailed_info={"passport_series_number": "1234 567 890",
                                                                      "passport_issued_by": "UFMS Russia",
                                                                      "passport_issued_date": "2013-01-01"})
        with self.expect_error(errors.CustomerEmailIsNotConfirmed):
            self.admin_client.customer.make_prod(customer_id)

        customer_db = Customer.get_by_id(customer_id)
        customer_db.confirm_email()

        customer = Customer.get_by_id(customer_id)
        customer.confirm_email()
        customer = self.admin_client.customer.make_prod(customer_id)

        self.assertEqual(customer["customer_mode"], "pending_prod")

        customer = self.admin_client.customer.update_balance(customer_id, Decimal("-1.0"), "updated by test")
        self.assertEqual(customer['customer_mode'], "pending_prod")

        customer = self.admin_client.customer.update_balance(customer_id, Decimal("1.0"), "updated by test")
        self.verify_production_state(customer, balance=Decimal("1.0"))

    @patch('task.customer.clean_up_customer_service_usage', MagicMock())
    def test_prepay_customer_make_prod_by_admin(self):
        password = "asdCustomer%"
        prepay_entity_customer = {"email": "email@email.ru", "customer_type": "entity", "detailed_info": {
            "name": "test prepay entity customer", "contract_number": "2015/4568",
            "contract_date": "2015-01-01", "organization_type": "OOO", "name": "Some Company",
            "full_organization_name": "OOO Some Company", "primary_state_registration_number": "159 8525 15552",
            "individual_tax_number": "52 59 5555555", "legal_address_country": "RU", "legal_address_city": "NN",
            "legal_address_address": "Ошарская, 13", "location_country": "RU", "location_city": "NN",
            "location_address": "Ошарская", "general_manager_name": "Васильев Е.В",
            "general_accountant_name": "Иванова В.Н", "contact_person_name": "Петров Василий"
        }}
        self.admin_client.auth(self.email, self.password)
        customer_id = self.admin_client.customer.create(password=password, **prepay_entity_customer)["customer_id"]
        self.admin_client.customer.update(customer_id, balance_limit="-10")
        customer = Customer.get_by_id(customer_id)
        customer.modify_balance(Decimal("-3.33"), "rub", self.admin_user.user_id, "")
        customer.confirm_email()

        self.admin_client.customer.update(customer_id, detailed_info={"contact_person_position": "CTO",
                                                                      "contact_telephone": "123456",
                                                                      "contact_email": "vasilii@mail.ga"})
        customer = self.admin_client.customer.make_prod(customer_id)
        self.verify_production_state(customer, balance=Decimal("0"), balance_limit=Decimal("-10"))

    @patch('task.customer.clean_up_customer_service_usage', MagicMock())
    def test_self_make_prod_by_customer(self):
        password = "asdCustomer%"
        private_customer = self.new_customer.copy()
        private_customer.update({"customer_type": "private"})
        customer_id = self.cabinet_client.customer.create(password=password, **private_customer)["customer_id"]
        self.admin_client.auth(self.email, self.password)
        customer = Customer.get_by_id(customer_id)
        customer.confirm_email()

        self.cabinet_client.customer.update("me", detailed_info={"passport_series_number": "1234 567 890",
                                                                 "passport_issued_by": "UFMS Russia",
                                                                 "passport_issued_date": "2013-01-01"})

        with self.expect_error(errors.BadRequest):
            self.cabinet_client.customer.update("me", detailed_info={"telephone": "11111111111111111"})

        customer = self.cabinet_client.customer.make_prod("me")
        self.assertEqual(customer["customer_mode"], "pending_prod")
        self.assertEqual(customer["customer_type"], "private")

        customer = self.admin_client.customer.update_balance(customer["customer_id"], Decimal("1.0"), "updated by test")
        self.verify_production_state(customer, balance=Decimal("1.0"))

        private_customer = self.new_customer.copy()
        private_customer.update({"customer_type": "private"})
        private_customer.update({"email": "2@email.ru"})
        customer_id = self.cabinet_client.customer.create(password=password, **private_customer)["customer_id"]
        self.admin_client.auth(self.email, self.password)
        customer = Customer.get_by_id(customer_id)
        customer.modify_balance(Decimal("3.33"), "rub", self.admin_user.user_id, "")
        customer.confirm_email()

        self.cabinet_client.customer.update("me", detailed_info={"passport_series_number": "1234 567 890",
                                                                 "passport_issued_by": "UFMS Russia",
                                                                 "passport_issued_date": "2013-01-01"})

        self.cabinet_client.customer.make_prod("me")
        customer = self.admin_client.customer.get(customer_id)
        self.verify_production_state(customer, balance=Decimal("3.33"))

    def test_balance(self):
        password = "balance"
        cust_info = self.cabinet_client.customer.create(password=password, **self.new_customer)
        self.assertEqual(cust_info["account"], {"RUB": {'balance': '0.00', 'current': '0.00', 'withdraw': '0.00'}})

        cust_info = self.admin_client.customer.update_balance(cust_info["customer_id"],
                                                              "1123.22", "test balance update")
        rub = cust_info["account"]["RUB"]
        self.assertEqual(rub["balance"], "1123.22")

        cust_info = self.admin_client.customer.update_balance(cust_info["customer_id"], "-88", "charge")
        rub = cust_info["account"]["RUB"]
        self.assertEqual(rub["balance"], "1035.22")

        cust = Customer.get_by_id(cust_info["customer_id"])
        cust.withdraw(Decimal("123.45678901"), "rub")
        db.session.commit()

        cust_info = self.admin_client.customer.get(cust_info["customer_id"])
        rub = cust_info["account"]["RUB"]
        self.assertEqual(rub["balance"], "1035.22")
        self.assertEqual(rub["current"], "911.76")
        self.assertEqual(rub["withdraw"], "123.46")

        history = self.admin_client.customer.balance_history(cust_info["customer_id"])
        self.assertEqual(len(history), 3)
        self.assertIn("user", history[0])

        history = self.cabinet_client.customer.balance_history("me")
        self.assertEqual(len(history), 3)
        self.assertNotIn("user", history[0])

    def test_force_delete_customer(self):
        password = "force_delete"

        self.cabinet_client.customer.create(password=password, email="test_email@example.com",
                                            detailed_info={"name": "$test customer"})
        self.cabinet_client.customer.create(password=password, email="test_email2@example.com",
                                            detailed_info={"name": "$other customer"})
        self.admin_client.customer.create(password=password, email="test_email3@example.com",
                                          customer_type="entity", detailed_info={"name": "$test customer 2"})

        deleted = self.admin_client.delete("/api/0/_force_delete/",
                                           {"prefix": "$test", "tables": "customer", "field": "name"}).json["deleted"]
        self.assertEqual(deleted["customer"], 2)

    def test_force_delete_customer_with_cards(self):
        created_customer = self.cabinet_client.customer.create(
            password="force_delete", email="test_email4@example.com",
            detailed_info={"name": "$test customer 3"})

        customer_id = created_customer['customer_id']

        CustomerCard.add_card(customer_id, '0000', 0, 'dummy_token', True)
        delete_params = {"prefix": "$test", "tables": "customer",
                         "field": "name"}
        self.admin_client.delete("/api/0/_force_delete/", delete_params).json["deleted"]
        cards = CustomerCard.query.filter_by(customer_id=customer_id)
        self.assertEqual(cards.count(), 0)

    def do_password_reset_from_email(self, new_password):
        token = re.findall(r"/set-password/([^\s]+)\s?", outbox[1].body)[0]
        self.cabinet_client.customer.reset_password_valid(token)
        self.cabinet_client.customer.reset_password(token, new_password)
        return token

    def test_password_reset(self):
        password = "asdCustomer%"
        customer_id = self.cabinet_client.customer.create(password=password, **self.new_customer)['customer_id']
        self.assertTrue(Customer.get_by_id(customer_id))
        old_password = password
        self.cabinet_client.customer.request_reset_password(self.new_customer['email'])
        self.assertEquals(len(outbox), 2)

        new_password = "new_password12345"
        token = self.do_password_reset_from_email(new_password)
        self.assertNotEqual(old_password, Customer.get_by_email(self.new_customer['email']).password)

        # ensure token is no longer active
        with self.expect_error(errors.PasswordResetTokenInvalid):
            self.cabinet_client.customer.reset_password_valid(token)

        with self.expect_error(errors.PasswordResetTokenInvalid):
            self.cabinet_client.customer.reset_password(token, new_password)

        self.cabinet_client.customer.request_reset_password(self.new_customer['email'])
        with self.expect_error(errors.PasswordResetTokenInvalid):
            self.do_password_reset_from_email("1")

    def test_get_filtered_customers(self):
        self.admin_client.customer.create(password="123qwe", email="1@email.ru")
        customer2 = self.admin_client.customer.create(password="123qwe", email="2@email.ru", customer_type="entity")
        customer3 = self.admin_client.customer.create(password="123qwe", email="3@email.ru")
        customer4 = self.admin_client.customer.create(password="123qwe", email="4@email.ru")
        customer5 = self.admin_client.customer.create(password="123qwe", email="5@email.ru", customer_type="entity")

        tariff_data = {
            "localized_name": self.localized_name("New tariff"),
            "description": "One more tariff",
            "currency": "RUB",
            "services": []
        }
        new_tariff_id = self.admin_client.tariff.create(as_json=True, **tariff_data)["tariff_id"]
        self.admin_client.tariff.immutable(new_tariff_id)
        self.admin_client.customer.update(customer2["customer_id"], tariff=new_tariff_id)
        self.admin_client.customer.update(customer3["customer_id"], tariff=new_tariff_id)

        all_customers = self.admin_client.customer.list()
        self.assertEqual(len(all_customers["items"]), 5)

        filtered_customers = self.admin_client.customer.list(tariff_ids=new_tariff_id)
        self.assertEqual(filtered_customers["total"], 2)
        for item in filtered_customers["items"]:
            self.assertEqual(item["tariff_id"], new_tariff_id)

        db.session.add(self.tariff)

        tariff_list = [str(new_tariff_id), str(self.tariff.tariff_id)]
        filtered_customers = self.admin_client.customer.list(tariff_ids=tariff_list)
        self.assertEqual(filtered_customers["total"], 5)

        new_name = "New Customer"
        self.admin_client.customer.update(customer2["customer_id"], detailed_info={"name": new_name})
        self.admin_client.customer.update(customer4["customer_id"], detailed_info={"name": new_name})
        filtered_customers = self.admin_client.customer.list(name=new_name)

        self.assertEqual(filtered_customers["total"], 2)
        for item in filtered_customers["items"]:
            self.assertEqual(item["detailed_info"]["name"], new_name)

        filtered_customers = self.admin_client.customer.list(tariff_ids=new_tariff_id, name=new_name)
        self.assertEqual(filtered_customers["total"], 1)
        self.assertEqual(filtered_customers["items"][0]["detailed_info"]["name"], new_name)

        self.admin_client.customer.delete(customer2["customer_id"])
        filtered_customers = self.admin_client.customer.list(name=new_name, visibility="deleted")
        self.assertEqual(filtered_customers["total"], 1)

        # Check only deleted customers in response
        filtered_customers = self.admin_client.customer.list(visibility="deleted")
        self.assertEqual(len(filtered_customers['items']), 1)
        self.assertEqual(filtered_customers['items'][0]['customer_id'], customer2['customer_id'])
        self.assertIsNotNone(filtered_customers['items'][0]['deleted'])

        # check filtering by creation date
        hour_ago = arrow.utcnow().replace(hours=-1).datetime
        in_hour = arrow.utcnow().replace(hours=+1).datetime

        filtered_customers = self.admin_client.customer.list(created_before=in_hour)
        self.assertEqual(len(filtered_customers['items']), 4)

        filtered_customers = self.admin_client.customer.list(created_before=hour_ago)
        self.assertEqual(len(filtered_customers['items']), 0)

        filtered_customers = self.admin_client.customer.list(created_after=in_hour)
        self.assertEqual(len(filtered_customers['items']), 0)

        filtered_customers = self.admin_client.customer.list(created_after=hour_ago)
        self.assertEqual(len(filtered_customers['items']), 4)

        filtered_customers = self.admin_client.customer.list()['items']
        self.assertEqual(
            [
                filtered_customers[0]['customer_id'], filtered_customers[1]['customer_id'],
                filtered_customers[2]['customer_id'], filtered_customers[3]['customer_id']
            ],
            [1, 3, 4, 5]
        )

        filtered_customers = self.admin_client.customer.list(sort='-email')['items']
        self.assertEqual(
            [
                filtered_customers[0]['customer_id'], filtered_customers[1]['customer_id'],
                filtered_customers[2]['customer_id'], filtered_customers[3]['customer_id']
            ],
            [5, 4, 3, 1]
        )

        filtered_customers = self.admin_client.customer.list(sort='tariff_id,email')['items']
        self.assertEqual(
            [
                filtered_customers[0]['customer_id'], filtered_customers[1]['customer_id'],
                filtered_customers[2]['customer_id'], filtered_customers[3]['customer_id']
            ],
            [1, 4, 5, 3]
        )

        filtered_customers = self.admin_client.customer.list(sort='tariff_id,-email')['items']
        self.assertEqual(
            [
                filtered_customers[0]['customer_id'], filtered_customers[1]['customer_id'],
                filtered_customers[2]['customer_id'], filtered_customers[3]['customer_id']
            ],
            [5, 4, 1, 3]
        )

        with self.expect_error(errors.BadRequest):
            self.admin_client.customer.list(sort='+email')

    def test_report_validators(self):
        customer = self.admin_client.customer.create(password="123qwe", email="2@email.ru")
        customer_id = customer["customer_id"]
        Customer.get_by_id(customer_id).confirm_email()
        now = arrow.utcnow().datetime

        start = now - timedelta(hours=3)
        end = now - timedelta(hours=2)

        start_future = now + timedelta(hours=3)
        end_future = now + timedelta(hours=5)

        with self.expect_error(errors.BadParameter):
            self.admin_client.customer.report(customer_id, start, end_future, report_format="json")

        with self.expect_error(errors.BadParameter):
            self.admin_client.customer.report(customer_id, start_future, end_future, report_format="json")

        with self.expect_error(errors.BadParameter):
            self.admin_client.customer.report(customer_id, end, start, report_format="json")

    def test_fake_usage(self):
        customer = self.admin_client.customer.create(password="123qwe", email="2@email.ru")
        customer_id = customer["customer_id"]
        start = datetime(2015, 7, 5, 3, 4, 5)
        finish = datetime(2015, 7, 8, 5, 7, 13)
        customer = Customer.get_by_id(customer_id)
        tenant = Tenant.create("tenant_id", "test")
        db.session.add(tenant)
        customer.os_tenant_id = tenant.tenant_id
        db.session.commit()
        self.admin_client.customer.fake_usage(customer_id, start, finish, "storage.disk", "v-1edfre", 10*conf.GIGA)

    @patch('os_interfaces.openstack_wrapper.openstack.get_limits', MagicMock(return_value=conf.template.default))
    def test_used_quotas(self):
        password = "asdCustomer%"
        customer = self.cabinet_client.customer.create(password=password, **self.new_customer)
        used_quotas = self.cabinet_client.customer.used_quotas('me')["used_quotas"]
        self.assertEqual(used_quotas, [])

        customer = Customer.get_by_id(customer['customer_id'])
        tenant = Tenant.create("tenant_id", "test")
        db.session.add(tenant)
        customer.os_tenant_id = tenant.tenant_id
        customer.os_user_password = '2'
        db.session.commit()
        used_quotas = self.cabinet_client.customer.used_quotas('me')
        self.assertEqual(used_quotas["loading"], True)

        used_quotas = self.cabinet_client.customer.used_quotas('me')["used_quotas"]
        self.assertEqual([list(item.keys())[0] for item in used_quotas],
                         [list(item.keys())[0] for item in conf.dashboard_quotas.groups])

        prepared_quotas = {}
        for item in [quota for item in used_quotas for quota in item.values()]:
            prepared_quotas.update({q["limit_id"]: q["value"] for q in item})
        template_dashboard_quotas = {}
        for group_quotas in [item for quota_group in conf.dashboard_quotas.groups for item in quota_group.values()]:
            for template_name in group_quotas:
                template_dashboard_quotas.update({template_name: conf.template.default[template_name]})
        self.assertDictEqual(prepared_quotas, template_dashboard_quotas)

        self.admin_client.customer.block(customer.customer_id)
        used_quotas = self.cabinet_client.customer.used_quotas('me')["used_quotas"]
        self.assertEqual(used_quotas, [])

    def customer_info(self, customer_name="test_customer"):
        return {"email": "%s@example.com" % customer_name,
                "password": customer_name + customer_name}

    def test_list(self):
        customer1 = self.cabinet_client.customer.create(**self.customer_info("customer1"))
        customer2 = self.cabinet_client.customer.create(**self.customer_info("customer2"))

        list1 = self.admin_client.customer.list()
        self.assertEqual(len(list1["items"]), 2)
        self.assertEqual(list1["total"], 2)

        self.admin_client.customer.delete(customer1["customer_id"])
        list2 = self.admin_client.customer.list()
        self.assertEqual(len(list2["items"]), 1)
        self.assertEqual(list2["total"], 1)
        self.assertEqual(list2["items"][0]["customer_id"], customer2["customer_id"])

        list3 = self.admin_client.customer.list(visibility="all")
        self.assertEqual(len(list3["items"]), 2)
        self.assertEqual(list3["total"], 2)

        list4 = self.admin_client.customer.list(visibility="deleted")
        self.assertEqual(len(list4["items"]), 1)
        self.assertEqual(list4["total"], 1)
        self.assertEqual(list4["items"][0]["customer_id"], customer1["customer_id"])

    def test_customer_delete(self):
        customer = self.cabinet_client.customer.create(**self.customer_info("customer1"))
        self.admin_client.customer.delete(customer["customer_id"])
        with self.expect_error(errors.CustomerInvalidToken):
            self.cabinet_client.customer.get("me")

        with self.expect_error(errors.CustomerRemoved):
            self.admin_client.customer.update(customer["customer_id"], password="new_password")

    def test_report_without_confirm(self):
        self.cabinet_client.customer.create(**self.customer_info("customer"))
        now = arrow.utcnow().datetime
        with self.expect_error(errors.CustomerEmailIsNotConfirmed):
            self.cabinet_client.customer.report("me", now - timedelta(days=1), now , report_format="json")

    def test_reset_os_password(self):
        password = "asdCustomer%"
        customer_id = self.cabinet_client.customer.create(password=password, **self.new_customer)['customer_id']

        with self.expect_error(errors.CustomerWithoutHorizonUser):
            self.cabinet_client.customer.reset_os_password()

        confirm_token = re.findall(r"/confirmation/([^\s]+)\s?", outbox[0].body)[0]
        self.cabinet_client.customer.confirm_email(confirm_token)
        customer = Customer.get_by_id(customer_id)

        old_password = customer.os_user_password

        self.cabinet_client.customer.reset_os_password()
        customer = Customer.get_by_id(customer_id)

        self.assertEqual(len(outbox), 3)
        self.assertNotEqual(old_password, customer.os_user_password)

        self.admin_client.customer.block(customer_id, blocked=True)
        with self.expect_error(errors.CustomerBlocked):
            self.cabinet_client.customer.reset_os_password()

    @mock.patch("conf.promocodes")
    def test_customer_signup_promocodes(self, conf_promocodes):
        conf_promocodes.promo_registration_only = True
        today = arrow.utcnow().date()
        conf_promocodes.codes = {
            'valid_code': today + timedelta(days=10),
            'expired':    today,
        }

        # Check valid promocode
        res = self.cabinet_client.customer.create(password="customercustomer", withdraw_period='week',
                                                  promo_code='valid_code', **self.new_customer)
        expected_code_value = [{"value": "valid_code"}]
        self.assertEqual(res['promo_code'], expected_code_value)

        # Check customer info
        customer_me_info = self.cabinet_client.customer.get("me")
        self.assertEqual(customer_me_info['promo_code'], expected_code_value)

        customer_admin_info = self.admin_client.customer.get(res["customer_id"])
        self.assertEqual(customer_admin_info['promo_code'], expected_code_value)

        # Check expired promocode
        with self.expect_error(errors.PromocodeInvalid):
            self.cabinet_client.customer.create(password="customercustomer",
                                                withdraw_period='week',
                                                promo_code='expired',
                                                **self.new_customer)

        # Check invalid promocode
        with self.expect_error(errors.PromocodeInvalid):
            self.cabinet_client.customer.create(password="customercustomer",
                                                withdraw_period='week',
                                                promo_code='invalid_code',
                                                **self.new_customer)

        # Check empty promocode
        with self.expect_error(errors.PromocodeOnly):
            self.cabinet_client.customer.create(password="customercustomer",
                                                withdraw_period='week',
                                                **self.new_customer)


        conf_promocodes.promo_registration_only = False

        # Registrations without codes and it's value later
        new_customer = self.new_customer.copy()
        new_customer.update({"email": "email_2nd_user@email.ru"})
        res_with_code = self.cabinet_client.customer.create(password="customercustomer",
                                                            withdraw_period='week',
                                                            promo_code='some_code',
                                                            **new_customer)
        self.assertEqual(res_with_code['promo_code'], [])

        new_customer.update({"email": "email_3rd_user@email.ru"})
        res_without_code = self.cabinet_client.customer.create(password="customercustomer",
                                                               withdraw_period='week',
                                                               **new_customer)
        self.assertEqual(res_without_code['promo_code'], [])

    def test_customer_cors(self):
        try:
            self.create_customer("asdf")
            self.assertFalse("Exception must be raised in line before")
        except ResponseError as response:
            self.assertIn("Access-Control-Allow-Origin", response.response.headers)

        self.create_customer("cors@mail.ru")
        response = self.admin_client.last_response
        self.assertIn("Access-Control-Allow-Origin", response.headers)

    def test_group_change(self):
        self.create_tariff("group_tariff")
        new_tariff = self.create_tariff("new_group_tariff")
        ids = []
        for n in range(10):
            customer_info = self.create_customer("%s@customer.ru" % n)
            ids.append(customer_info["customer_id"])
        res = self.admin_client.customer.group_update(ids[:7], tariff=new_tariff["tariff_id"])
        self.assertEqual(len(res), 7)
        customers = self.admin_client.customer.list()["items"]
        customers_with_new_tariff = [c for c in customers if c["tariff_id"] == new_tariff["tariff_id"]]
        self.assertEqual(len(customers_with_new_tariff), 7)

        res = self.admin_client.customer.group_update(ids[7:], tariff=new_tariff["tariff_id"],
                                                      deferred_date=arrow.utcnow().datetime + timedelta(seconds=2))

        for customer in res:
            deferred = Deferred(self.admin_client, customer["customer_id"])
            deferred.force()

        customers = self.admin_client.customer.list()["items"]
        customers_with_new_tariff = [c for c in customers if c["tariff_id"] == new_tariff["tariff_id"]]
        self.assertEqual(len(customers_with_new_tariff), 10)

    @mock.patch.object(openstack, 'get_auth_info', return_value=None)
    def test_os_token(self, os_auth_info):
        expected_result = {
            'token': {
                'audit_ids': ['123123123123123123'],
                'expires': '2015-10-02T16:35:28Z',
                'id': '12312312312312312312312312312312',
                'issued_at': '2015-10-02T15:35:28.151646',
                'tenant': {'description': 'Admin Project',
                           'enabled': True,
                           'id': '345345345534534534534534534',
                           'name': 'admin'}
            }}
        os_auth_info.return_value = expected_result

        customer1 = self.cabinet_client.customer.create(**self.customer_info("customer1"))
        confirm_token = re.findall(r"/confirmation/([^\s]+)\s?", outbox[0].body)[0]
        self.cabinet_client.customer.confirm_email(confirm_token)
        token = self.cabinet_client.customer.os_token()
        self.assertEqual(token.json, expected_result)
