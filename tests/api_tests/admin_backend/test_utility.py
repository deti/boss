from api_tests.admin_backend import AdminBackendTestCase


class TestUtility(AdminBackendTestCase):
    need_loggedin_client = False

    def test_country_list(self):
        countries = self.default_admin_client.utility.countries()
        self.assertGreater(len(countries), 0)

    def test_role_list(self):
        roles = self.default_admin_client.utility.role_list()
        self.assertGreater(len(roles), 0)

    def test_subscriptions_list(self):
        subscriptions = self.default_admin_client.utility.subscriptions()
        self.assertGreater(len(subscriptions), 0)

    def test_language_list(self):
        languages = self.default_admin_client.utility.languages()
        self.assertGreater(len(languages), 0)

    def test_language_active_list(self):
        languages = self.default_admin_client.utility.languages_active()
        self.assertGreater(len(languages), 0)

    def test_locale_list(self):
        locales = self.default_admin_client.utility.locales_active()
        self.assertGreater(len(locales), 0)