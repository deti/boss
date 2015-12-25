from api_tests.admin_backend import AdminBackendTestCase


class TestCurrency(AdminBackendTestCase):
    def test_currency_list(self):
        currencies = self.default_admin_client.currency.get()
        self.assertNotEqual(len(currencies), 0)

    def test_active_currency(self):
        currencies = self.default_admin_client.currency.get_active()
        self.assertNotEqual(len(currencies), 0)
