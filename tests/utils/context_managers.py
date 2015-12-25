import datetime
import configs
from clients import AdminBackendClient
from utils import mailtrap


class TemporaryLogout:
    """Simulate client logout by simply removing authorization token."""

    def __init__(self, client: AdminBackendClient):
        self.client = client

    def __enter__(self):
        self.token = self.client.session.cookies.pop('token')

    # noinspection PyUnusedLocal
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.session.cookies['token'] = self.token


class Mailtrap:
    """Cleanup all mail in mailtrap mailbox that created inside this context manager."""

    def __init__(self, clear: bool=True, prefix: str=None):
        self.clear = clear
        self.prefix = prefix
        self.start = datetime.datetime.now()
        self.api = mailtrap.MailTrapApi(configs.mailtrap.token)

    def __enter__(self) -> mailtrap.MailTrapApi:
        return self.api

    # noinspection PyUnusedLocal
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.clear:
            self.api.cleanup(created_after=self.start, prefix=self.prefix)
