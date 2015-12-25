from tests.base import TestCaseApi, ResponseError


class TestI18N(TestCaseApi):
    def test_i18n(self):
        try:
            self.admin_client.auth("xxx@yyy.ru", "yy")
            self.fail("Exception should be during auth")
        except ResponseError as e:
            self.assertIn("string length must be between", e.response.json["message"])
            self.assertIn("string length must be between", e.response.json["localized_message"])

        params = {"password": "yy", "email": "xxx@yyy.ru"}

        try:
            self.admin_client.post('/api/0/auth/', params, headers={"Accept-Language": "ru-RU"}, auth_required=False)
            self.fail("Exception should be during auth")
        except ResponseError as e:
            self.assertIn("string length must be between", e.response.json["message"])
            self.assertIn("длина строки должна", e.response.json["localized_message"])
