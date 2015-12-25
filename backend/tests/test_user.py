import errors
import re
from api import API_ADMIN
from tests.base import BaseTestCaseDB, TestCaseApi, ApiAdminClient
from model import User, db
from model.account.role import Role
from utils import mail


class TestUser(BaseTestCaseDB):
    def test_user_create(self):
        User.new_user("email@email.ru", "123qwe", "admin", "test user")
        db.session.flush()
        with self.assertRaises(errors.UserAlreadyExists):
            User.new_user("email@email.ru", "123qwe", "admin", "test user")
            db.session.flush()

        db.session.rollback()

        # conflict with user from fixtures
        with self.assertRaises(errors.UserAlreadyExists):
            User.new_user("boss@yourstack.com", "123qwe", "admin", "test user")
            db.session.flush()
        db.session.rollback()


class TestUserApi(TestCaseApi):
    new_user = {"email": "admin@yandex.ru", "password": "SuperHardPassword01234Я",
                "role": "admin", "name": "Superman Adminman"}

    def test_success_login(self):
        res = self.admin_client.auth(self.email, self.password)
        self.assertEqual(res, {})

        res = self.admin_client.auth(self.email, self.password, return_user_info=True)
        res.pop("user_id")
        res.pop("created")
        self.assertEqual(res, {'name': 'Super Admin', 'deleted': None,
                               'email': self.email,
                               'role': {'localized_name': {'en': 'Administrator', 'ru': 'Администратор'},
                                        'role_id': 'admin'}})

        self.admin_client.logout()
        with self.expect_error(errors.UserInvalidToken):
            self.admin_client.post("/api/0/user/", self.new_user, auth_required=False)

    def test_login_options(self):
        res = self.admin_client.options("/api/0/auth")
        self.assertEqual(res.headers["Content-Type"], "text/html")
        self.assertIn("Access-Control-Allow-Credentials", res.headers)
        self.assertIn("Access-Control-Allow-Headers", res.headers)
        self.assertIn("Access-Control-Allow-Methods", res.headers)
        self.assertIn("Access-Control-Allow-Origin", res.headers)

    def test_failed_login(self):
        # unknown user
        with self.expect_error(errors.Unauthorized):
            self.admin_client.auth(email="unknown@email.ru", password="unknown")
        # incorrect password
        with self.expect_error(errors.Unauthorized):
            self.admin_client.auth(email=self.email, password="xzzzzz")

    def generate_user(self, role, prefix=""):
        return {"email": "{}{}@mail.ru".format(prefix, role),
                "password": prefix + role + role,
                "role": role,
                "name": "Test {}{}".format(prefix, role)
                }

    def create_user(self, role, prefix=""):
        user = self.generate_user(role, prefix)
        self.admin_client.user.create(**user)
        return ApiAdminClient(self.get_app(API_ADMIN), user["email"], user["password"])

    def validate_create_user(self, client_role):
        client = self.create_user(client_role)

        for role in Role.higher_roles(client_role) | frozenset((client_role, )):
            user = self.generate_user(role, client_role + "_")
            with self.expect_error(errors.UserInvalidRole()):
                client.user.create(**user)

        for role in Role.lower_roles(client_role):
            user = self.generate_user(role, client_role + "_")
            client.user.create(**user)

    def test_create_user(self):
        self.admin_client.auth(self.email, self.password)
        res = self.admin_client.user.create(**self.new_user)
        self.assertEqual(res["user_info"]["name"], self.new_user["name"])

        with self.expect_error(errors.UserAlreadyExists):
            self.admin_client.user.create(**self.new_user)

        self.validate_create_user(Role.SUPPORT)
        self.validate_create_user(Role.MANAGER)
        self.validate_create_user(Role.ACCOUNT)

    def test_create_user_json(self):
        res = self.admin_client.user.create(as_json=True, **self.new_user)
        self.assertEqual(res["user_info"]["name"], self.new_user["name"])

    def test_invalid_encoding(self):
        res = self.admin_client.app.get(url="/api/0/user/", params={"name": b"\xf0\x28\x8c\x28"}, expect_errors=True)
        self.assertEqual(res.status_code, 400)

    def test_user_info(self):
        res = self.admin_client.user.get("me")["user_info"]
        user_id = res.pop("user_id")
        res.pop("created")
        self.assertEqual(res, {'name': 'Super Admin', 'deleted': None,
                               'email': self.email,
                               'role': {'localized_name': {'en': 'Administrator', 'ru': 'Администратор'},
                                        'role_id': 'admin'}})

        res = self.admin_client.user.get(user_id)["user_info"]
        res.pop("user_id")
        res.pop("created")
        self.assertEqual(res, {'name': 'Super Admin', 'deleted': None,
                               'email': self.email,
                               'role': {'localized_name': {'en': 'Administrator', 'ru': 'Администратор'},
                                        'role_id': 'admin'}})

        with self.expect_error(errors.BadParameter):
            self.admin_client.user.get("sadfasdfsadf")

        with self.expect_error(errors.UserNotFound):
            self.assertFalse(self.admin_client.user.get("121235328")["user_info"])

    def test_update_user(self):
        new_email = "new_email@yandex.ru"
        res = self.admin_client.user.update("me", email=new_email)["user_info"]
        self.assertEqual(res["email"], new_email)

        new_name = "Super Puper Admin"
        res = self.admin_client.user.update("me", name=new_name)["user_info"]
        self.assertEqual(res["name"], new_name)

        with self.expect_error(errors.NothingForUpdate):
            self.admin_client.user.update("me")

        with self.expect_error(errors.BadParameter):
            self.admin_client.user.update("me", password="pass")

        new_password = "password2"
        self.admin_client.user.update("me", password=new_password)

        with self.expect_error(errors.UserUnauthorized):
            self.admin_client.auth(self.email, self.password)

        with self.expect_error(errors.UserUnauthorized):
            self.admin_client.auth(res["email"], self.password)

        with self.expect_error(errors.UserUnauthorized):
            self.admin_client.auth(self.email, new_password)

        self.admin_client.auth(res["email"], new_password)

    def test_user_update_other(self):
        new_user = self.admin_client.user.create(**self.new_user)["user_info"]
        new_user_id = new_user["user_id"]
        new_email = "coadmin@yandex.ru"
        new_role = Role.MANAGER
        user_info = self.admin_client.user.update(new_user_id, email=new_email)["user_info"]
        self.assertEqual(user_info["email"], new_email)
        db.session.rollback()
        user_info = self.admin_client.user.get(new_user_id)["user_info"]
        self.assertEqual(user_info["email"], new_email)

        user_info = self.admin_client.user.update(new_user_id, role=new_role)["user_info"]
        self.assertEqual(user_info["role"]['role_id'], new_role)

    def test_self_user_remove(self):
        self.admin_client.user.delete("me")

        with self.expect_error(errors.UserInvalidToken):
            self.admin_client.user.update("me", email="new_email@emai.ru")

        with self.expect_error(errors.UserUnauthorized):
            self.admin_client.auth()

    def test_user_remove(self):
        new_user = self.admin_client.user.create(**self.new_user)["user_info"]

        user_client = ApiAdminClient(self.get_app(API_ADMIN), self.new_user["email"], self.new_user["password"])
        user_client.user.get("me")

        admin_user = self.admin_client.user.get("me")["user_info"]
        with self.expect_error(errors.HarakiriIsNotAllowed):
            self.admin_client.user.delete(admin_user["user_id"])

        self.admin_client.user.delete(new_user["user_id"])
        with self.expect_error(errors.UserInvalidToken):
            user_client.user.get("me")

        with self.expect_error(errors.UserUnauthorized):
            user_client.auth()

        with self.expect_error(errors.BadRequest):
            self.admin_client.user.delete("safasfasdff32w4,23")

        with self.expect_error(errors.UserNotFound):
            self.admin_client.user.delete("0")

    def test_renew_user(self):
        new_user = self.admin_client.user.create(**self.new_user)["user_info"]
        user_client = ApiAdminClient(self.get_app(API_ADMIN), self.new_user["email"], self.new_user["password"])
        user_client.user.get("me")

        self.admin_client.user.delete(new_user["user_id"])
        new_user2 = self.admin_client.user.create(**self.new_user)["user_info"]
        self.assertIsNone(new_user2["deleted"])
        self.assertEqual(new_user2["name"], self.new_user["name"])

    def test_user_list(self):
        self.assertEqual(len(self.admin_client.user.list(email=self.email)["user_list"]["items"]), 1)
        self.assertEqual(len(self.admin_client.user.list(email="sadfsdf")["user_list"]["items"]), 0)
        self.create_user(Role.ACCOUNT)
        self.create_user(Role.MANAGER)
        self.create_user(Role.SUPPORT)
        self.assertEqual(len(self.admin_client.user.list(role_list='admin,manager')["user_list"]["items"]), 2)
        self.assertEqual(len(self.admin_client.user.list(role_list='admin,account,manager,support')["user_list"]["items"]), 4)

        filtered_users = self.admin_client.user.list()["user_list"]["items"]
        self.assertEqual(
            [
                filtered_users[0]['user_id'], filtered_users[1]['user_id'],
                filtered_users[2]['user_id'], filtered_users[3]['user_id']
            ],
            [2,1,3,4]
        )

        filtered_users = self.admin_client.user.list(sort='role')["user_list"]["items"]
        self.assertEqual(
            [
                filtered_users[0]['user_id'], filtered_users[1]['user_id'],
                filtered_users[2]['user_id'], filtered_users[3]['user_id']
            ],
            [2,1,3,4]
        )

        filtered_users = self.admin_client.user.list(sort='-role')["user_list"]["items"]
        self.assertEqual(
            [
                filtered_users[0]['user_id'], filtered_users[1]['user_id'],
                filtered_users[2]['user_id'], filtered_users[3]['user_id']
            ],
            [4,3,1,2]
        )

        self.create_user(Role.ACCOUNT, prefix='b')

        filtered_users = self.admin_client.user.list(sort='role,email')["user_list"]["items"]
        self.assertEqual(
            [
                filtered_users[0]['user_id'], filtered_users[1]['user_id']
            ],
            [2,5]
        )

        filtered_users = self.admin_client.user.list(sort='role,-email')["user_list"]["items"]
        self.assertEqual(
            [
                filtered_users[0]['user_id'], filtered_users[1]['user_id']
            ],
            [5,2]
        )

        with self.expect_error(errors.BadRequest):
            self.admin_client.user.list(sort='+email')

    def test_create_user_without_password_and_activate_it(self):
        user = self.generate_user("admin", "wp")
        user.pop("password")
        self.admin_client.user.create(**user)

        self.assertEquals(len(mail.outbox), 1)
        new_password = "new_password12345"
        self.do_password_reset_from_email(new_password)

        user["password"] = new_password
        self.admin_client.auth(email=user["email"], password=new_password)

    def do_password_reset_from_email(self, new_password):
        token = re.findall(r"/set-password/([^\s]+)\s?", mail.outbox[0].body)[0]
        self.admin_client.user.reset_password_valid(token)
        self.admin_client.user.reset_password(token, new_password)
        return token

    def test_password_reset(self):
        user = User.get_by_email(self.email)
        old_password = user.password
        self.admin_client.user.request_reset_password(self.email)
        self.assertEquals(len(mail.outbox), 1)

        new_password = "new_password12345"
        token = self.do_password_reset_from_email(new_password)
        self.assertNotEqual(old_password, User.get_by_email(self.email).password)

        # ensure token is no longer active
        with self.expect_error(errors.PasswordResetTokenInvalid):
            self.admin_client.user.reset_password_valid(token)

        with self.expect_error(errors.PasswordResetTokenInvalid):
            self.admin_client.user.reset_password(token, new_password)

        self.admin_client.user.request_reset_password(self.email)
        with self.expect_error(errors.PasswordResetTokenInvalid):
            self.do_password_reset_from_email("1")
