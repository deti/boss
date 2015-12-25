import entities
from nose_parameterized import parameterized
from api_tests.admin_backend import AdminBackendTestCase
from utils.context_managers import TemporaryLogout


class TestUserRoles(AdminBackendTestCase):
    def test_admin_user_role(self):
        self.assertEqual(self.default_admin_client.user.get()['role']['role_id'], 'admin')

    def test_role_creation_higher(self):
        _, _, account_client = self.create_user('account', with_client=True)

        with self.assertRaisesHTTPError(405):
            account_client.user.create(**entities.AdminCredentials(self).generate())

    def test_role_creation_equal(self):
        _, _, account_client = self.create_user('account', with_client=True)

        with self.assertRaisesHTTPError(405):
            account_client.user.create(**entities.AdminCredentials(self).generate(role='account'))


class UserSimpleTests(AdminBackendTestCase):
    def test_relogin_tokens(self):
        client = self.get_admin_client(False)
        client.login(**self.get_default_admin_credentials())
        old_token = client.token
        client.login(**self.get_default_admin_credentials())
        self.assertNotEqual(old_token, client.token)
        client.logout()

        with self.assertRaisesHTTPError(401):
            client.user.get()

    def test_user_conflict_creation(self):
        user_info = self.create_user()[0]

        with self.assertRaisesHTTPError(409):
            self.create_user(email=user_info['email'])

    def test_login_options(self):
        resp = self.default_admin_client.login_options()
        self.assertEqual(len(resp), 0)
        self.assertTrue("Content-Type" in self.default_admin_client.last.headers)
        self.assertEqual(self.default_admin_client.last.headers['Content-Type'], "text/html")
        self.assertTrue("Access-Control-Allow-Methods" in self.default_admin_client.last.headers)
        self.assertEqual(self.default_admin_client.last.headers["Access-Control-Allow-Methods"], "POST, OPTIONS")

    def test_user_logout_operations(self):
        with TemporaryLogout(self.default_admin_client):
            with self.assertRaisesHTTPError(401):
                self.default_admin_client.user.get()
            with self.assertRaisesHTTPError(401):
                self.default_admin_client.user.get(self.default_admin_client.user_id)

    def test_user_get_info_invalid_id(self):
        with self.assertRaisesHTTPError(404):
            self.default_admin_client.user.get(192857198)

    def test_user_self_remove(self):
        user_info, credentials, user_client = self.create_user(with_client=True)
        self.assertFalse(user_info['deleted'])

        user_client.user.delete()

        with self.assertRaisesHTTPError(401):
            user_client.user.get()

        with self.assertRaisesHTTPError(401):
            user_client.login(credentials['email'], credentials['password'])

        with self.assertRaisesHTTPError(409):
            self.default_admin_client.user.delete(user_info['user_id'])

    def test_user_invalid_password_auth(self):
        user_info, credentials = self.create_user()
        with self.assertRaisesHTTPError(401):
            self.get_admin_client(False, credentials['email'], self.generate_password())


class TestUserList(AdminBackendTestCase):
    def setUp(self):
        super().setUp()
        self.user_info, _ = self.create_user()

    def search_user_in_list(self, user_list):
        for user in user_list['items']:
            if user['user_id'] == self.user_info['user_id']:
                break
        else:
            self.fail('User {} not found in user list {}'.format(self.user_info['email'], user_list['items']))

    def test_list_by_email(self):
        user_list = self.default_admin_client.user.list(email=self.user_info['email'])
        self.search_user_in_list(user_list)

    def test_list_by_name(self):
        user_list = self.default_admin_client.user.list(name=self.user_info['name'])
        self.search_user_in_list(user_list)


class TestUserUpdate(AdminBackendTestCase):
    def setUp(self):
        super().setUp()
        self.user_info, _, self.user_client = self.create_user(role='support', with_client=True)

    def test_user_update_self(self):
        new_name = self.create_name('медвед')
        self.user_info = self.user_client.user.update(name=new_name)
        self.assertEqual(self.user_info['name'], new_name)

        user_info = self.user_client.user.get()
        self.assertEqual(user_info['name'], new_name)

        with self.assertRaisesHTTPError(400):
            self.user_client.user.update()

    def test_user_update_by_admin(self):
        new_name = self.create_name('медвед')
        self.user_info = self.default_admin_client.user.update(self.user_info['user_id'], name=new_name)
        self.assertEqual(self.user_info['name'], new_name)

        user_info = self.default_admin_client.user.get(self.user_info['user_id'])
        self.assertEqual(user_info['name'], new_name)

    @parameterized.expand([
        ['account'],
        ['manager'],
        ['support']
    ])
    def test_user_update_not_by_admin(self, role:str=None):
        if role is None:
            return

        _, _, user_client = self.create_user(role, with_client=True)

        with self.assertRaisesHTTPError(405):
            user_client.user.update(self.user_info['user_id'], email=self.user_info['email'])

    def test_self_remove(self):
        with self.assertRaisesHTTPError(405):
            self.user_client.user.delete(self.user_info['user_id'])

    def test_remove_by_admin(self):
        self.default_admin_client.user.delete(self.user_info['user_id'])

        with self.assertRaisesHTTPError(409):
            self.default_admin_client.user.delete(self.user_info['user_id'])


class TestUserEmails(AdminBackendTestCase):
    def test_new_user_no_password_email_sends(self):
        self.cleanup_mailtrap(delayed=True)

        email = self.generate_mailtrap_email()
        self.create_user('account', email=email, password=None)
        match = self.search_email(r'set-password/(?P<token>\w+)')
        self.assertTrue(match)

    def test_password_reset_unkown_email(self):
        email = self.generate_email()
        with self.assertRaisesHTTPError(404):
            self.default_admin_client.user.request_password_reset(email)

    def test_password_reset_invalid_token(self):
        invalid_token = 'invalidtoken'

        with self.assertRaisesHTTPError(400):
            self.default_admin_client.user.validate_password_reset(invalid_token)

        with self.assertRaisesHTTPError(400):
            self.default_admin_client.user.password_reset(invalid_token, self.generate_password())

    def test_password_resetting(self):
        self.cleanup_mailtrap(delayed=True)

        email = self.generate_mailtrap_email()
        _, _, user_client = self.create_user('account', email=email, with_client=True)

        user_client.user.request_password_reset(email)

        match = self.search_email(r'set-password/(?P<token>\w+)')
        self.assertTrue(match)

        password_token = match.group('token')

        user_client.user.validate_password_reset(password_token)

        new_password = self.generate_password()

        user_client.user.password_reset(password_token, new_password)

        with self.assertRaisesHTTPError(401):
            user_client.user.get()

        user_client.login(email, new_password)
