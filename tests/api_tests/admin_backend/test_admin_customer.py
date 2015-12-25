import datetime

from api_tests.admin_backend import AdminBackendTestCase
from requests import HTTPError


class SimpleAdminCustomerTests(AdminBackendTestCase):
    def setUp(self):
        super().setUp()
        self.customer, _, self.customer_client = self.create_customer(create_default_tariff=True, with_client=True)

    def test_customer_history(self):
        history = self.default_admin_client.customer.history(self.customer['customer_id'])
        for item in history:
            if item['event'] == 'created':
                break
        else:
            self.fail('Created event not found in customer history')

    def test_customer_subscribitions_list_by_admin(self):
        subscribe = self.default_admin_client.customer.subscription.get(self.customer['customer_id'])
        self.assertGreater(len(subscribe), 0)

        old_subscribe = self.default_admin_client.customer.subscription.get(self.customer['customer_id'])
        self.default_admin_client.customer.subscription.update(self.customer['customer_id'], {'news':{'enable': not old_subscribe['news']['enable'], 'email':[]}})
        subscribe = self.default_admin_client.customer.subscription.get(self.customer['customer_id'])
        self.assertNotEqual(subscribe['news']['enable'], old_subscribe['news']['enable'])

    def test_customer_tariff_update(self):
        tariff = self.create_tariff()

        with self.assertRaisesHTTPError(409):
            self.default_admin_client.customer.update(self.customer['customer_id'], tariff=tariff['tariff_id'])

        self.default_admin_client.tariff.immutable(tariff['tariff_id'])

        self.customer = self.default_admin_client.customer.update(self.customer['customer_id'], tariff=tariff['tariff_id'])
        self.assertEqual(self.customer['tariff_id'], tariff['tariff_id'])

    def test_customer_tariff_update_deleted(self):
        tariff = self.create_tariff(immutable=True)
        self.default_admin_client.tariff.delete(tariff['tariff_id'])
        with self.assertRaisesHTTPError(409):
            self.default_admin_client.customer.update(self.customer['customer_id'], tariff=tariff['tariff_id'])

    def test_customer_account_history(self):
        history = self.default_admin_client.customer.balance_history(self.customer['customer_id'])
        self.assertGreater(len(history), 0)
        for item in history:
            if item['comment'] == 'Initial test balance':
                break
        else:
            self.fail('"Initial test balance" not found in account history:'+str(history))

    def search_in_quota_info(self, limit_id, limit_value, quota_list):
        for quota in quota_list:
            if quota['limit_id'] == limit_id and quota['value'] == limit_value:
                break
        else:
            self.fail('Quote not found for {} ({} - {}): {}'.format(self.customer['name'],
                                                                    limit_id, limit_value, quota_list))

    def test_customer_change_quota(self):
        limit_value = 50
        limit_id = 'router'

        quota_info = self.default_admin_client.customer.quota.update(self.customer['customer_id'],
                                                                     {limit_id: limit_value})
        self.search_in_quota_info(limit_id, limit_value, quota_info)

        quota_info = self.default_admin_client.customer.quota.get(self.customer['customer_id'])
        self.search_in_quota_info(limit_id, limit_value, quota_info)

        quota_info = self.customer_client.customer.quota()
        self.search_in_quota_info(limit_id, limit_value, quota_info)

    def test_change_quota_template(self):
        template_list = self.default_admin_client.utility.quota_templates()
        template_id = template_list[0]['template_id']
        limit_id = template_list[0]['template_info'][0]['limit_id']
        limit_value = template_list[0]['template_info'][0]['value']
        new_limit_value = limit_value + 1

        quota_info = self.default_admin_client.customer.quota.update(self.customer['customer_id'],
                                                                     {limit_id: new_limit_value})
        self.search_in_quota_info(limit_id, new_limit_value, quota_info)

        self.default_admin_client.customer.quota.update_template(self.customer['customer_id'], template_id)

        quota_info = self.default_admin_client.customer.quota.get(self.customer['customer_id'])
        self.search_in_quota_info(limit_id, limit_value, quota_info)


class TestGroupUpdate(AdminBackendTestCase):
    def test_customer_group_update(self):
        new_tariff = self.create_tariff()
        customer_info_1, _, customer_client_1 = self.create_customer(True, with_client=True)
        customer_info_2, _, customer_client_2 = self.create_customer(True, with_client=True)
        customer_ids = (customer_info_1['customer_id'], customer_info_2['customer_id'])

        new_balance_limit = float(customer_info_1['balance_limit'])+float(customer_info_2['balance_limit']) + 1.50
        customers = ','.join(map(str, customer_ids))

        self.default_admin_client.customer.group_update(customers, balance_limit=str(new_balance_limit))

        customer_info_1 = customer_client_1.customer.get()
        customer_info_2 = customer_client_2.customer.get()
        self.assertEqual(float(customer_info_1['balance_limit']), new_balance_limit)
        self.assertEqual(float(customer_info_2['balance_limit']), new_balance_limit)

        deferred_date = self.make_datetime(datetime.datetime.today()+datetime.timedelta(days=1))

        with self.assertRaisesHTTPError(409):
            self.default_admin_client.customer.group_update(customers, tariff=new_tariff['tariff_id'], deferred_date=deferred_date)

        self.default_admin_client.tariff.immutable(new_tariff['tariff_id'])
        self.default_admin_client.customer.group_update(customers, tariff=new_tariff['tariff_id'], deferred_date=deferred_date)

        list(map(self.default_admin_client.customer.deferred.force, customer_ids))

        customer_info_1 = customer_client_1.customer.get()
        customer_info_2 = customer_client_2.customer.get()
        self.assertEqual(customer_info_1['tariff_id'], new_tariff['tariff_id'])
        self.assertEqual(customer_info_2['tariff_id'], new_tariff['tariff_id'])

        default_tariff = self.check_default_tariff()
        self.default_admin_client.customer.group_update(customers, tariff=default_tariff['tariff_id'])

        customer_info_1 = customer_client_1.customer.get()
        customer_info_2 = customer_client_2.customer.get()
        self.assertEqual(customer_info_1['tariff_id'], default_tariff['tariff_id'])
        self.assertEqual(customer_info_2['tariff_id'], default_tariff['tariff_id'])


class DeferredChangesTests(AdminBackendTestCase):
    def setUp(self):
        super().setUp()
        self.customer, _, self.customer_client = self.create_customer(create_default_tariff=True, with_client=True)
        self.addCleanupBeforeDelete(self.default_admin_client.customer.deferred.delete, self.customer['customer_id'])

    def test_setting_deferred_changes(self):
        deferred = self.default_admin_client.customer.deferred.get(self.customer['customer_id'])
        self.assertIsNone(deferred)

        with self.assertRaisesHTTPError(404):
            self.default_admin_client.customer.deferred.force(self.customer['customer_id'])

        new_tariff = self.create_tariff()
        date = self.make_datetime(datetime.datetime.today() + datetime.timedelta(days=1))

        with self.assertRaisesHTTPError(409):
            self.default_admin_client.customer.deferred.update(self.customer['customer_id'], new_tariff['tariff_id'], date)

        self.default_admin_client.tariff.immutable(new_tariff['tariff_id'])

        self.default_admin_client.customer.deferred.update(self.customer['customer_id'], new_tariff['tariff_id'], date)
        deferred = self.default_admin_client.customer.deferred.get(self.customer['customer_id'])
        self.assertEqual(new_tariff['tariff_id'], deferred['tariff']['tariff_id'])
        #self.assertEqual(date, deferred['date'])
        self.default_admin_client.customer.deferred.force(self.customer['customer_id'])
        tariff_info = self.default_admin_client.customer.tariff.get(self.customer['customer_id'])
        self.assertEqual(tariff_info['tariff_id'], new_tariff['tariff_id'])

    def test_setting_deferred_deleted_tariff(self):
        new_tariff = self.create_tariff(immutable=True)
        date = self.make_datetime(datetime.datetime.today() + datetime.timedelta(days=1))
        self.default_admin_client.customer.deferred.update(self.customer['customer_id'], new_tariff['tariff_id'], date)
        with self.assertRaisesHTTPError(409):
            self.default_admin_client.tariff.delete(new_tariff['tariff_id'])
        self.default_admin_client.customer.deferred.force(self.customer['customer_id'])


class CustomerBlockingTests(AdminBackendTestCase):
    block_message = 'Hello, world!'

    def test_customer_is_blocked(self):
        self.customer, _, self.customer_client = self.create_customer(create_default_tariff=True, confirmed=True,
                                                                      with_client=True, need_openstack=True)
        self.customer_client.customer.os_login()
        self.default_admin_client.customer.block(self.customer['customer_id'], True, self.block_message)

        self.customer = self.customer_client.customer.get()
        self.assertTrue(self.customer['blocked'])

        with self.assertRaisesHTTPError(409):
            self.customer_client.customer.os_login()


class CustomerUnblockingTests(AdminBackendTestCase):
    block_message = 'Hello, world!'

    def test_have_openstack_access(self):
        self.customer, _, self.customer_client = self.create_customer(create_default_tariff=True, confirmed=True,
                                                                      with_client=True, need_openstack=True)
        self.default_admin_client.customer.block(self.customer['customer_id'], True, self.block_message)
        self.customer = self.default_admin_client.customer.block(self.customer['customer_id'], False)

        self.assertFalse(self.customer['blocked'])

        for r in self.retries(30):
            with r:
                try:
                    self.customer_client.customer.os_login()
                except HTTPError as e:
                    if e.response.status_code == 400:
                        raise AssertionError('Openstack access check failed')


class DeletedCustomerTests(AdminBackendTestCase):
    def setUp(self):
        super().setUp()
        self.customer, _, self.customer_client = self.create_customer(create_default_tariff=True, with_client=True)
        self.default_admin_client.customer.delete(self.customer['customer_id'])

    def test_customer_deleted(self):
        self.assertTrue(self.default_admin_client.customer.get(self.customer['customer_id'])['deleted'])

        with self.assertRaisesHTTPError(409):
            self.default_admin_client.customer.delete(self.customer['customer_id'])

    def test_customer_cant_use_api(self):
        with self.assertRaisesHTTPError(401):
            self.customer_client.customer.get()

    def test_customer_update_fails(self):
        with self.assertRaisesHTTPError(409):
            self.default_admin_client.customer.update(self.customer['customer_id'], detailed_info=dict(city=self.customer['detailed_info']['city']))

        with self.assertRaisesHTTPError(409):
            self.default_admin_client.customer.subscription.update(self.customer['customer_id'], {'news':{'enable': True, 'email':[]}})

    def test_deleted_customer_not_in_list(self):
        customer_list = self.default_admin_client.customer.list()['items']
        for customer in customer_list:
            if customer['customer_id'] == self.customer['customer_id']:
                self.fail('Deleted customer found in customer list.')

    def test_sending_confirm_email(self):
        with self.assertRaisesHTTPError(409):
            self.default_admin_client.customer.send_confirm_email(self.customer['customer_id'])
