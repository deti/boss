from api_tests.admin_backend import AdminBackendTestCase


class TestQuotes(AdminBackendTestCase):
    def test_quotes_templates(self):
        templates_list = self.default_admin_client.utility.quota_templates()
        self.assertGreater(len(templates_list), 0)
        for template in templates_list:
            self.assertIn('template_id', template)
            self.assertIn('template_info', template)
            template_info = template['template_info']
            for limit_info in template_info:
                self.assertIn('limit_id', limit_info)
                self.assertIn('value', limit_info)
                self.assertIn('localized_description', limit_info)
