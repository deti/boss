"""
Shortcut module for all clients to be used in system tests, with some test-related settings.
"""

from boss_client import adminbackend, cabinetbackend, HTTPError
import openstack_client
import configs


class AdminBackendClient(adminbackend.AdminBackendClient):
    @staticmethod
    def client_settings():
        return {'server_address': configs.backend.entry_point, "secret_key": configs.api.secure.secret_key}

    @classmethod
    def create_loggedin(cls, email:str, password:str) -> adminbackend.AdminBackendClient:
        c = cls.create_default()
        c.login(email, password)
        return c

    @classmethod
    def create_default_loggedin(cls) -> adminbackend.AdminBackendClient:
        return cls.create_loggedin(**configs.default_admin)


class CabinetBackendClient(cabinetbackend.CabinetBackendClient):
    @staticmethod
    def client_settings():
        return {'server_address': configs.backend.entry_point, "secret_key": configs.api.secure.secret_key}

    @classmethod
    def create_loggedin(cls, email:str, password:str) -> cabinetbackend.CabinetBackendClient:
        c = cls.create_default()
        c.login(email, password)
        return c


class OpenstackClient(openstack_client.OpenstackClient):
    pass