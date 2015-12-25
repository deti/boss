import inspect
import json
import pprint
import requests
import time
import logbook
from requests.exceptions import HTTPError
from boss_client.auth import Signature
from urllib.parse import urlsplit


class BaseApiClient:
    HTTP_TIMEOUT = 1
    API_VERSION = 0
    API_PREFIX = '/api/' + str(API_VERSION)
    BOT_SECRET = "bot_secret"
    email = None
    last = None
    password = None

    @classmethod
    def create_default(cls):
        return cls(**cls.client_settings())

    @staticmethod
    def client_settings() -> dict:
        raise NotImplementedError

    def __init__(self, server_address: str='', secret_key: str=''):
        if not server_address:
            server_address = 'http://127.0.0.1:8080'
        self.server_address = server_address
        self.session = requests.Session()
        self.signature = Signature(secret_key) if secret_key else None

    @classmethod
    def create_default(cls):
        settings = cls.client_settings()
        return cls(settings['server_address'], settings["secret_key"])

    def login(self, *args, **kwargs):
        raise NotImplementedError

    def logout(self):
        raise NotImplementedError

    def _build_url(self, command) -> str:
        command = str(command).strip()
        if not command.startswith('/'):
            command = self.API_PREFIX + '/' + command
        if self.server_address.endswith('/') and command.startswith('/'):
            return self.server_address[:-1]+command
        return self.server_address+command

    def _send(self, url:str, method: str='get', expected_status: int=200, **kwargs):
        method = method.lower().strip()
        bot_secret = kwargs.pop('bot_secret', None)
        json_data = kwargs.pop('json_data', False)
        if bot_secret and self.signature:
            url_path = urlsplit(url).path
            signature = self.signature.calculate_signature(time.time(), method, url_path, kwargs["data"])
            if 'data' not in kwargs:
                kwargs['data'] = dict()
            if isinstance(kwargs['data'], dict):
                kwargs['data'][self.BOT_SECRET] = signature
        if 'data' in kwargs:
            if json_data:
                kwargs['data'] = json.dumps(kwargs['data'])
                if 'headers' in kwargs:
                    kwargs['headers'].update({'Content-type': 'application/json', 'Accept': 'text/plain'})
                else:
                    kwargs['headers'] = {'Content-type': 'application/json', 'Accept': 'text/plain'}
            elif isinstance(kwargs['data'], dict):
                for key, value in kwargs['data'].items():
                    if isinstance(value, (dict, set, list)):
                        kwargs['data'][key] = json.dumps(value)
        with _LoggingContextManager(self, method, url, expected_status, kwargs) as logging:
            raw_data = getattr(self.session, method)(url, **kwargs)
        logging.log(raw_data)
        self.last = raw_data
        if raw_data.status_code != expected_status:
            raise HTTPError("Return status %s %s is as not expected %s: %s" %
                            (raw_data.status_code, raw_data.reason, expected_status, raw_data.content),
                            response=raw_data)
        if 'json' in raw_data.headers.get('content-type', ''):
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

    @property
    def loggedin(self) -> bool:
        return bool(self.token)

    @property
    def token(self) -> str:
        return self.session.cookies.get('token', '')


class _LoggingContextManager:
    counter = 0

    def __init__(self, client:BaseApiClient, method, url, expected_status, kwargs):
        self.client = client
        self.method = method
        self.url = url
        self.expected_status = expected_status
        self.kwargs = kwargs
        _LoggingContextManager.counter += 1

    def __enter__(self):
        self.start = time.time()
        self._log_start()
        return self

    def _log_start(self):
        message = self.cstr + ' Start'
        if self.client.loggedin:
            message += ' "{}"'.format(self.client.email)
        message += ' {} {} ({})'.format(self.method, self.url, self.expected_status)
        logbook.debug(message)
        if len(self.kwargs) > 0:
            logbook.debug(self.cstr + ' Params {}'.format(json.dumps(self.kwargs)))

    def _log_end(self):
        message = self.cstr + ' End'
        message += ' elapsed {}'.format(round(self.elapsed, 4))
        logbook.debug(message)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end = time.time()
        self.elapsed = self.end - self.start
        self._log_end()

    def log(self, response:requests.Response):
        message = self.cstr + ' Response'
        data = None
        if 'content-type' in response.headers and 'json' in response.headers['content-type']:
            data = '\n' + pprint.pformat(response.json(), width=121)
        else:
            data = pprint.pformat(response.text[:1024], width=121)
        if data:
            message += ' ' + data
        if response.status_code != self.expected_status:
            if response.status_code < 500:
                logbook.warning(message)
            else:
                logbook.error(message)
        else:
            logbook.debug(message)

    @property
    def cstr(self) -> str:
        return '[{}]'.format(_LoggingContextManager.counter)


def extract_parameters(no_id:bool=False) -> dict:
    """
    Return current function arguments and their names.
    Assume you have:
    def func(self, foo, bar, baz):  # self or cls is mandatory
        d = extract_parameters()

    If you call func(1, 'foo', 'hello'), then in d you will get {'foo': 1, 'bar': 'foo', 'baz': 'hello'}
    """
    frame = inspect.currentframe().f_back
    func_name = frame.f_code.co_name
    func_locals = inspect.getargvalues(frame)[3]
    if func_name in frame.f_globals:
        func = frame.f_globals[func_name]
    else:
        if 'self' in func_locals:
            func = getattr(func_locals['self'], func_name)
        elif 'cls' in func_locals:
            func = getattr(func_locals['cls'], func_name)
        else:
            raise KeyError('Cannot get func object for {}. Maybe it is @staticmethod?'.format(func_name))
    signature = inspect.signature(func)
    parameters = dict()
    for param_name in signature.parameters.keys():
        if param_name in func_locals:
            parameters[param_name] = func_locals[param_name]
    if 'kwargs' in parameters and isinstance(parameters['kwargs'], dict):
        parameters.update(parameters.pop('kwargs'))
    if 'args' in parameters and isinstance(parameters['args'], tuple):
        raise ValueError('Cant process *args parameters')
    for key, value in list(parameters.items()):
        if value is None or (no_id and key.endswith('_id')):
            parameters.pop(key)
    if 'self' in parameters:
        parameters.pop('self')
    if 'cls' in parameters:
        parameters.pop('cls')
    return parameters


class Namespace:
    path = None

    def __init__(self, client:BaseApiClient):
        self.client = client

    def __str__(self):
        if self.path:
            return self.path
        return super().__str__()

    def __add__(self, other):
        if isinstance(other, str):
            return str(self) + other

    def __call__(self, *args, **kwargs):
        if self.path:
            return self.path.format(*args, **kwargs)
