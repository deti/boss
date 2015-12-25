from tests.base import TestCaseApi


class TestCurrencyApi(TestCaseApi):
    def test_currency(self):
        self.assertTrue(self.admin_client.currency.list())
        self.assertTrue(self.admin_client.currency.list_active())
