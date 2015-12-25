import json
import requests


class ApiClientBase:
    API_VERSION = 0
    API_PREFIX = '/api/' + str(API_VERSION)

    def __init__(self, server_address:str):
        """
        :param str server_address: Backend url like http://localhost:8080
        """
        self.server_address = server_address
        self.session = requests.Session()

    def _build_url(self, command) -> str:
        command = str(command).strip()
        if not command.endswith('/') and not command.startswith('/'):
            command += '/'
        if not command.startswith('/'):
            command = self.API_PREFIX + '/' + command
        if self.server_address.endswith('/') and command.startswith('/'):
            return self.server_address[:-1]+command
        return self.server_address+command

    def _send(self, url:str, method: str='get', expected_status: int=200, **kwargs):
        method = method.lower().strip()
        json_data = kwargs.pop('json_data', False)
        if json_data:
            kwargs['data'] = json.dumps(kwargs['data'])
            if 'headers' in kwargs:
                kwargs['headers'].update({'Content-type': 'application/json', 'Accept': 'text/plain'})
            else:
                kwargs['headers'] = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        raw_data = getattr(self.session, method)(url, **kwargs)
        self.last = raw_data
        self.last_data = kwargs.get('data', None)
        if raw_data.status_code != expected_status:
            raise raw_data.raise_for_status()
        if 'content-type' in raw_data.headers and 'json' in raw_data.headers['content-type']:
            return raw_data.json()
        else:
            return raw_data.content

    def send_command(self, command:str, method:str='get', expected_status:int=200, **kwargs):
        return self._send(self._build_url(command), method, expected_status, **kwargs)

    def send_command_get(self, command, expected_status:int=200, **kwargs):
        return self.send_command(command, 'get', expected_status, **kwargs)

    def send_command_post(self, command, expected_status:int=200, **kwargs):
        return self.send_command(command, 'post', expected_status, **kwargs)

    def send_command_put(self, command, expected_status:int=200, **kwargs):
        return self.send_command(command, 'put', expected_status, **kwargs)

    def send_command_delete(self, command, expected_status:int=200, **kwargs):
        return self.send_command(command, 'delete', expected_status, **kwargs)

    def send_command_options(self, command, expected_status:int=200, **kwargs):
        return self.send_command(command, 'options', expected_status, **kwargs)


class AdminBackendClient(ApiClientBase):
    def version(self):
        return self.send_command_get('/api/version/')

    def user_get(self):
        return self.send_command_get('user/me/')

    def user_update(self, name):
        return self.send_command_put('user/me/', data=dict(name=name))

    def login(self, email, password):
        return self.send_command_post('auth/', data=dict(email=email, password=password))

    def logout(self):
        return self.send_command_post('logout/')

    def tariff_list(self):
        return self.send_command_get('tariff/')

    def send_email(self, send_to, subject=None, cc=None):
        return self.send_command_post('send_email/', data=dict(send_to=send_to, subject=subject))

    def tariff_get_default(self):
        return self.send_command_get('tariff/default/')

    def countries(self):
        return self.send_command_get('country/')

    def role_list(self):
        return self.send_command_get('role/')


class CabinetBackendClient(ApiClientBase):
    API_VERSION = 0
    API_PREFIX = '/lk_api/' + str(API_VERSION)

    def login(self, email, password):
        return self.send_command_post('auth/', data=dict(email=email, password=password, return_customer_info=True))

    def reset_os_password(self):
        return self.send_command_put('customer/me/reset_os_password/')

    def os_login(self):
        return self.send_command_get('customer/me/os_login/')