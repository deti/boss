import contextlib
import os
from utils.base import BaseTestCase


class TestDatabaseFalling(BaseTestCase):
    @classmethod
    def check_database(cls):
        cls.default_admin_client.user.get()

    @classmethod
    def drop_database(cls):
        os.system('service mysql stop')

    @classmethod
    def raise_database(cls):
        os.system('service mysql start')

    @classmethod
    @contextlib.contextmanager
    def drop_database_context(cls):
        cls.drop_database()
        try:
            yield
        finally:
            cls.raise_database()

    @classmethod
    def tearDownClass(cls):
        cls.raise_database()

    def test_database_falling(self):

        self.check_database()

        with self.drop_database_context(), self.assertRaisesHTTPError(503):
            self.check_database()

        self.check_database()
