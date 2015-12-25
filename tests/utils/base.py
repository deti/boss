from collections import namedtuple
import datetime
import string
import time
import unittest
import unittest.case
import threading
from contextlib import contextmanager

import posixpath
import re
import logbook

import configs
import entities
from utils.mailtrap import MailTrapApi
from utils.tools import generate_token, format_backend_datetime
from clients import HTTPError, AdminBackendClient, CabinetBackendClient
from lib.logger import setup_logbook


class _MyAssertRaisesContext(unittest.case._AssertRaisesContext):
    """
    Checks if response status code matches expected status code.
    Generally used to test code that must rise HTTPError.
    """
    def __init__(self, expected, test_case, expected_status:int=None, expected_message:str=None):
        """
        :param expected: Expected error class.
        :param test_case: Test case instance.
        :param expected_status: expected response status.
        :param expected_message: expected response message (TODO).
        :return:
        """
        super().__init__(expected, test_case)
        self.expected_status = expected_status
        self.expected_message = expected_message

    def __exit__(self, exc_type, exc_val, exc_tb):
        v = super().__exit__(exc_type, exc_val, exc_tb)
        if self.expected_status:
            if exc_type is HTTPError and self.expected_status != exc_val.response.status_code:
                # TODO: handle message
                self._raiseFailure('Response status code {} doesnt match expected {}: {}'.format(
                    exc_val.response.status_code, self.expected_status, exc_val.response.text))
        elif exc_type is None:
            self._raiseFailure('HTTPError not raised.')
        return v


class BaseTestCase(unittest.TestCase):
    ids_used = set()
    lock = threading.Lock()
    current_method = None
    need_loggedin_client = True

    if need_loggedin_client:
        default_admin_client = AdminBackendClient.create_default_loggedin()
    else:
        default_admin_client = AdminBackendClient.create_default()

    _force_delete_order = ['customer', 'tariff', 'user', 'news', 'service']
    _table_field = {'customer': 'name', 'tariff': 'localized_name', 'user': 'name', 'news': 'subject',
                    'service': 'localized_name'}

    logbook.info("Run tests for region: {} and availability zone: {}", configs.region, configs.availability_zone)

    def __init__(self, *args, **kwargs):
        self._cleanup_before_force_delete = list()  # [(func, args, kwargs), ...]
        self._cleanup_force_delete = dict()  # table -> [(prefix, field), ...]
        self._cleanup_after_delete = list()  # [(func, args, kwargs), ...]
        super().__init__(*args, **kwargs)

    def setUp(self):
        self.__class__._current_method_name = self._testMethodName
        logbook.info("--------------- setUp {} ---------------", self)

    def tearDown(self):
        self.__class__._current_method_name = None
        logbook.info("============== tearDown {} ================", self)

    @classmethod
    def setUpClass(cls):
        if not configs.logging.initialized:
            handler = setup_logbook("system_tests", configs.logging)
            handler.push_application()
            configs.logging.initialized = True
        cls._current_method_name = 'setUpClass'
        logbook.info("--------------- setUpClass {} ---------------", cls)

    @classmethod
    def tearDownClass(cls):
        logbook.info("--------------- tearDownClass {} ---------------", cls)
        cls._current_method_name = 'tearDownClass'

    def assertInList(self, seq, check_func:callable, message:str='Item not found in list'):
        """
        Shortcut function to search something in an iterable object.
        Raise AssertionError with provided message if item not found.
        Return item that check_func(item) == True.

        :param iterable seq: list, tuple, etc.
        :param callable check_func: function that will be called with every item of seq. Must return bool.
        :param str message: Message to raise if item not found.
        :return: item that check_func(item) == True.
        """
        for item in seq:
            if check_func(item):
                return item
        else:
            self.fail(message)

    def cleanup_mailtrap(self, prefix=None, delayed:bool=False):
        """
        Remove all messages from mailtrap mailbox that match specified prefix.
        If prefix is None, use current test prefix.

        :param str prefix: prefix for message.
        :param delayed: call this function after current test ends, after force delete.
        """
        if prefix is None:
            prefix = self.get_test_prefix()
        else:
            prefix = self.clear_email_chars(prefix)
        if delayed:
            self.addCleanupAfterDelete(self.cleanup_mailtrap, prefix)
            return
        MailTrapApi.create_default().cleanup(prefix=prefix)

    @classmethod
    def generate_password(cls) -> str:
        """Generate a common password with 8 symbols length."""
        return generate_token(8, 0)

    @classmethod
    def get_current_name(cls, full: bool=False):
        """
        Return current test name. Usually it is ClassName.test_name.
        If not full, it is test_name.
        Current test name is stored in class attribute _current_method_name.
        If it is abcent or None, return ClassName.
        """
        name = cls.__name__
        if hasattr(cls, '_current_method_name') and cls._current_method_name is not None:
            if cls._current_method_name not in {'setUpClass', 'tearDownClass'}:
                if full:
                    name += '.' + cls._current_method_name
                else:
                    name = cls._current_method_name
        return name

    @classmethod
    def _base_test_prefix(cls) -> str:
        """
        Return base test prefix. It consists of test prefix, region, availability zone and tests start time,
        all separated by underscores. Used as part of generated names for tests entities.
        """
        prefix = configs.devel.test_prefix + '_'
        region = configs.region
        az = configs.availability_zone
        region_az = region + '_'
        if az != region:
            region_az += az + '_'
        dt = datetime.datetime.fromtimestamp(configs.load_time)
        return cls.clear_email_chars(prefix + region_az + dt.strftime('%m-%d_%H-%M'))

    @classmethod
    def get_test_prefix(cls, func_name: str=None, truncate: bool=True):
        """Return test prefix, which consists of base test prefix and current function name (if func_name is None)."""
        prefix = cls._base_test_prefix()
        if func_name is None:
            func_name = cls.get_current_name()
        length_limit = configs.customer_name_max_length - configs.id_length - 1 - configs.additional_name_length - 1
        test_prefix = prefix + '_' + func_name
        if truncate:
            test_prefix = test_prefix[:length_limit]
        return cls.clear_email_chars(test_prefix)

    @classmethod
    def create_name(cls, additional: str=None) -> str:
        """
        Create name for current test entity. Add an additional to generated name.
        Name consists of current test prefix, additional (if provided) and unique ID.

        :param str additional: will be truncated by additional_name_length
        """
        name = cls.get_test_prefix()
        if additional is not None:
            additional = additional[:configs.additional_name_length]
            name += '_' + additional
        return name + '_' + cls.generate_id()

    @classmethod
    def generate_email(cls, domain: str='example.com') -> str:
        """
        Generate email for current test. It is created name for current test with @+domain at end.

        :param str domain: email domain (without @).
        :return: email.
        """
        return cls.create_name() + '@' + domain

    @classmethod
    def generate_mailtrap_email(cls) -> str:
        """Shortcut to generate email with mailtrap.io domain"""
        return cls.generate_email('mailtrap.io')

    def assertRaisesHTTPError(self, expected_status:int=None, expected_message:str=None):
        """Assert if code block raises HTTPError with specified status and message or not."""
        return _MyAssertRaisesContext(HTTPError, self, expected_status, expected_message)

    @classmethod
    def retries(cls, timeout=5, sleep_time=0.5, exception=AssertionError, sleep=time.sleep):
        """
        This generator function yields context manager for timeout seconds with sleep_time interval.
        If code inside context manager raises an error exception, then suspress and and continue
        if timeout is not exceeded. If timeout is exceeded and error is not exception, then stop iteration and raise it.

        For example:
        for r in self.retries(timeout=60):
            with r:
                self.assertTrue(self.is_email_confirmed())

        The code under context manager will continue to be called for timeout seconds
        until self.is_email_confirmed() is True.
        If self.is_email_confirmed() wont go True for 60 seconds, it will raise common assertion error.
        :return: generator function that yields context manager.
        """
        timeout_at = time.time() + timeout
        state = {"fails_count": 0, "give_up": False, "success": False}
        while time.time() < timeout_at:
            yield cls._handler(exception, state)
            if state["success"]:
                return
            sleep(sleep_time)
        state["give_up"] = True
        yield cls._handler(exception, state)

    @classmethod
    @contextmanager
    def _handler(cls, exception, state):
        try:
            yield
        except exception:
            state["fails_count"] += 1
            if state["give_up"]:
                raise
        else:
            state["success"] = True

    @classmethod
    def generate_id(cls, attemts: int=20):
        """Generate a unique id for current id session"""
        with cls.lock:
            for _ in range(attemts):
                token = generate_token(configs.id_length)
                if token in cls.ids_used:
                    continue
                cls.ids_used.add(token)
                return token
            raise ValueError()

    @classmethod
    def clear_email_chars(cls, email: str) -> str:
        """Remove characters that not allowed in email address."""
        email_chars = string.ascii_letters + string.digits + '#-_~!$&\'()*+,;='
        domain = None
        if '@' in email:
            email, domain = email.split('@')
        return ''.join(filter(lambda x: x in email_chars, email)) + ('@' + domain if domain else '')

    @classmethod
    def search_email(cls, regexp: str, prefix:str=None, timeout: int=60, dotall:bool=False):
        """
        Search an email in mailtrap mailbox with prefix, which body matches regexp (re.search).
        Raise AssertionError if none matched.

        :param regexp regexp: regular expression to search in email body.
        :param str prefix: email address prefix. Current test prefix used if None.
        :param int timeout: searching timeout.
        :param bool dotall: use re.DOTALL.
        :return: match object.
        """
        if prefix is None:
            prefix = cls.get_test_prefix()
        mailtrap_api = MailTrapApi.create_default()
        regexp = re.compile(regexp, re.DOTALL if dotall else 0)
        for r in cls.retries(timeout=timeout):
            with r:
                messages = mailtrap_api.get_messages(prefix=prefix)
                for message in messages:
                    match = regexp.search(message['text_body'])
                    if match:
                        logbook.debug('Got match in: {}'.format(message['text_body']))
                        return match
                else:
                    raise AssertionError('Emails with prefix {} matching pattern "{}" not found. {} tried.'.format(
                        prefix, regexp.pattern, len(messages)))

    @classmethod
    def confirm_customer(cls, prefix, client: CabinetBackendClient=None):
        """
        Confirm customer email by searching an email with confirmation token and confirming it with cabinet client.

        :param prefix: Can be either full email part (before @) or a simple .
        """
        match = cls.search_email(r'confirmation/(?P<token>\w+)', prefix)
        token = match.group('token')
        if client is None:
            client = cls.get_cabinet_client()
        client.customer.confirm_email(token)

    def get_openstack_credentials(self, customer_info:dict, prefix=None) -> tuple:
        self.assertIsNotNone(customer_info['os_username'])
        if prefix is None:
            prefix = self.get_test_prefix()
        match = self.search_email('OpenStack login: (?P<login>[-\w]+).*?'
                                  'OpenStack password: (?P<password>.+?)\s.*?'
                                  'OpenStack Keystone API: (?P<auth_url>.+?)\s',
                                  prefix=prefix, dotall=True)
        OpenstackCredentials = namedtuple('OpenstackCredentials', ['tenant_id', 'username', 'password', 'auth_url'])
        return OpenstackCredentials(customer_info['os_tenant_id'], customer_info['os_username'], match.group('password'), match.group('auth_url').strip())

    @classmethod
    def make_datetime(cls, dt: datetime.datetime) -> str:
        """Shortcut for formatting datetime in backend format."""
        return format_backend_datetime(dt)

    @classmethod
    def get_admin_client(cls, loggedin_default: bool=True, email: str=None, password: str=None) -> AdminBackendClient:
        """
        Return admin backend client object.

        :param bool loggedin_default: return client that authorized as default admin.
        :param email: user email.
        :param password: user password.
        :return AdminBackendClient: admin backend client object.
        """
        if loggedin_default and not email and not password:
            if cls.need_loggedin_client:
                return cls.default_admin_client
            else:
                return AdminBackendClient.create_default_loggedin()
        elif email and password:
            return AdminBackendClient.create_loggedin(email, password)
        else:
            return AdminBackendClient.create_default()

    @classmethod
    def get_cabinet_client(cls, email: str=None, password: str=None) -> CabinetBackendClient:
        """
        Return cabinet backend client object.

        :param email: customer email.
        :param password: customer password.
        :return: cabinet backend client object.
        """
        if email and password:
            return CabinetBackendClient.create_loggedin(email, password)
        else:
            return CabinetBackendClient.create_default()

    @classmethod
    def force_delete(cls, table, prefix=None, field=None) -> int:
        """
        Run force delete.

        :param table: table to force delete on.
        :param prefix: entity name prefix (current test prefix if None).
        :param field: table field (get from _table_field attribute by default).
        :return int: count of deleted objects.
        """
        if prefix is None:
            prefix = cls.get_test_prefix()
        if field is None:
            field = cls._table_field[table]
        count = None

        class BadHTTPError(HTTPError): pass

        try:
            for r in cls.retries(60, 1, exception=BadHTTPError):
                with r:
                    try:
                        count = cls.default_admin_client.utility.force_delete(table, prefix, field)['deleted'][table]
                    except HTTPError as e:
                        if e.response.status_code > 500:
                            raise BadHTTPError(response=e.response, request=e.request)
                        raise
        except:
            logbook.exception('Force delete error of {}, prefix={}, field={}'.format(table, prefix, field))
            raise
        else:
            if count == 0:
                method = logbook.warning
            else:
                method = logbook.info
            method('Force delete {} objects of {}, prefix={}, field={}'.format(count, table, prefix, field))
        return count

    def addCleanupBeforeDelete(self, func, *args, **kwargs):
        """Add cleanup function to run before force_delete."""
        self._cleanup_before_force_delete.append((func, args, kwargs))

    def addCleanupDelete(self, table, prefix=None, field=None):
        """Add force delete of table in cleanups."""
        if prefix is None:
            prefix = self.get_test_prefix()
        if field is None:
            field = self._table_field[table]
        if table not in self._cleanup_force_delete:
            self._cleanup_force_delete[table] = list()
        if prefix not in self._cleanup_force_delete[table]:
            self._cleanup_force_delete[table].append((prefix, field))

    def addCleanupAfterDelete(self, func, *args, **kwargs):
        """Add cleanup function to run after force_delete."""
        self._cleanup_after_delete.append((func, args, kwargs))

    def doCleanups(self):
        """
        Run cleanups for current test. This cleanups will run EVEN if setUp of test fails.
        Original doCleanups will be called AFTER.
        """
        outcome = self._outcome or unittest.case._Outcome()

        def generic_cleanup(source):
            while source:
                function, args, kwargs = source.pop()
                logbook.debug('Executing cleanup: {}'.format(function))
                with outcome.testPartExecutor(self):
                    function(*(args or tuple()), **(kwargs or {}))

        generic_cleanup(self._cleanup_before_force_delete)
        for table in self._force_delete_order:
            if table in self._cleanup_force_delete:
                while self._cleanup_force_delete[table]:
                    prefix, field = self._cleanup_force_delete[table].pop()
                    logbook.debug('Executing cleanup: Force delete {} with prefix "{}"'.format(table, prefix))
                    with outcome.testPartExecutor(self):
                        self.force_delete(table, prefix, field)
        generic_cleanup(self._cleanup_after_delete)
        generic_cleanup(self._cleanups)
        return outcome.success

    def create_user(self, role: str=entities.AdminCredentials.default_role, email_domain: str='example.com',
                    with_client: bool=False, **kwargs):
        """
        Create admin backend user.

        :param str role: user role.
        :param str email_domain: user email domain.
        :param bool with_client: return third item as admin backend cliend authorized as created user.
        :param dict kwargs: kwargs passed to entity generation function.
        :return tuple: user_info, user credentials if not with_client, else user_info, user credentials, client
        """
        self.addCleanupDelete('user')
        if 'email' not in kwargs:
            kwargs['email'] = self.generate_email(email_domain)
        credentials = entities.AdminCredentials(self).generate(role=role, **kwargs)
        user_info = self.default_admin_client.user.create(**credentials)
        if not with_client:
            return user_info, credentials
        else:
            client = self.get_admin_client(email=credentials['email'], password=credentials['password'])
            return user_info, credentials, client

    def create_service(self, immutable: bool=False, **kwargs) -> dict:
        """
        Create service.

        :param bool immutable: make created service immutable.
        :param dict kwargs: kwargs passed to entity generation function.
        :return dict: service_info
        """
        self.addCleanupDelete('service')
        info = entities.Service(self).generate(**kwargs)
        client = self.get_admin_client()
        service_info = self.default_admin_client.service.create(**info)
        if immutable:
            service_info = client.service.immutable(service_info['service_id'])
        return service_info

    def create_news(self, published: bool=False, **kwargs) -> dict:
        """
        Create news.

        :param bool published: make created news published.
        :param dict kwargs: kwargs passed to entity generation function.
        :return dict: news_info
        """
        self.addCleanupDelete('news')
        info = entities.News(self).generate(**kwargs)
        news_info = self.default_admin_client.news.create(**info)
        if published:
            news_info = self.default_admin_client.news.publish(news_info['news_id'], True)
        return news_info

    def check_default_tariff(self):
        """Check if default tariff exists. If True, return its tariff_info"""
        try:
            return self.default_admin_client.tariff.get_default()
        except HTTPError as e:
            if e.response.status_code == 404:
                message = self.default_admin_client.last.json()
                if message['message'] == 'Plan not found':
                    return
            raise

    def restore_default_tariff(self):
        """If default tariff exists, make it default back in cleanups. Return default tariff info"""
        default_tariff = self.check_default_tariff()
        if default_tariff:
            self.addCleanupBeforeDelete(self.default_admin_client.tariff.set_default, default_tariff['tariff_id'])
        return default_tariff

    def get_or_create_default_tariff(self) -> tuple:
        """
        Create default tariff if it not exists, otherwise return existing default tariff.

        :return dict, bool: tariff_info, bool created
        """
        tariff = self.check_default_tariff()
        if tariff is None:
            return self.create_tariff(set_default=True, immutable=True), True
        else:
            return tariff, False

    def create_tariff(self, services: list=None, parent_id: int=None, set_default: bool=False, immutable: bool=False,
                      **kwargs) -> dict:
        """
        Create tariff.

        :param list services: list of tuples[(service_id, service price)].
        :param int parent_id: tariff parent id.
        :param bool immutable: set created tariff immutable.
        :param bool set_default: set created tariff as default (only if immutable is true too).
        :param dict kwargs: kwargs passed to entity generation function.
        :return dict: tariff_info
        """
        self.addCleanupDelete('tariff')
        if services is not None:
            services = [{'service_id': service_id, 'price': price} for service_id, price in services]
        info = entities.Tariff(self).generate(services=services, parent_id=parent_id, **kwargs)
        tariff_info = self.default_admin_client.tariff.create(**info)
        if immutable:
            tariff_info = self.default_admin_client.tariff.immutable(tariff_info['tariff_id'])
        if set_default and immutable:
            tariff_info = self.default_admin_client.tariff.set_default(tariff_info['tariff_id'])
        return tariff_info

    def create_customer(self, create_default_tariff: bool=False, email_domain: str='example.com', confirmed: bool=False,
                        with_client: bool=False, individual: bool=False, entity: bool=False, go_prod: bool=False,
                        need_openstack: bool=False, with_promocode:bool=None, make_full_prod:bool=False,
                        by_admin: bool=False, mailtrap_email: bool=False, **kwargs):
        """
        Create customer.

        :param bool create_default_tariff: create default tariff if not exists.
        :param str email_domain: customer email domain.
        :param bool confirmed: confirm created customers email.
        :param bool with_client: return cabinet client authorized as created customer.
        :param bool individual: add individual fields to customers info.
        :param bool entity: add entity fields to customers info.
        :param bool go_prod: switch created customer to production mode(only if individual or entity is true).
        :param bool need_openstack: wait for openstack creation (only if confirmed).
        :param bool with_promocode: use promocode in registration.
        :param bool make_full_prod: update customer balance with some money to switch him from pending to production mode (only if go_prod).
        :param bool by_admin: create customer by admin backend.
        :param bool mailtrap_email: generate mailtrap email.
        :param dict kwargs: kwargs passed to entity generation function.
        :return tuple: customer_info, customer credentials if not with_client, else customer_info, customer credentials, client
        """
        self.addCleanupDelete('customer')
        if 'email' not in kwargs:
            if mailtrap_email:
                kwargs['email'] = self.generate_mailtrap_email()
                self.cleanup_mailtrap(delayed=True)
            else:
                kwargs['email'] = self.generate_email(email_domain)
        if with_promocode is not None:
            kwargs['with_promocode'] = with_promocode
        credentials = entities.CustomerCredentials(self).generate(individual=individual, entity=entity, **kwargs)
        if create_default_tariff:
            self.get_or_create_default_tariff()
        client = self.get_cabinet_client()
        if not by_admin:
            customer_info = client.customer.create(**credentials)
        else:
            customer_info = self.default_admin_client.customer.create(**credentials)
        client.login(credentials['email'], credentials['password'])
        if confirmed:
            self.default_admin_client.customer.update(customer_info['customer_id'], confirm_email=True)
            self.wait_openstack(customer_info['customer_id'], delayed=not need_openstack)
            customer_info = client.customer.get()
        if (entity or individual) and go_prod:
            customer_info = client.customer.make_prod()
            if make_full_prod:
                customer_info = self.default_admin_client.customer.update_balance(
                    customer_info['customer_id'], 1,
                    'Automatic balance update during customer creation in system tests')
        if with_client:
            return customer_info, credentials, client
        return customer_info, credentials

    def wait_openstack(self, customer_id: int, timeout: int=90, delayed:bool=False):
        """
        Wait for customer's openstack creation by repeatly checking customer_info[os_tenant_id] and expecting not None.

        :param int customer_id: customer id.
        :param int timeout: wait timeout.
        :param bool delayed: call this function after current test ends, before force delete.
        :return dict: customer_info
        """
        if delayed:
            self.addCleanupBeforeDelete(self.wait_openstack, customer_id, timeout)
            return
        logbook.debug('Waiting openstack for {}'.format(customer_id))
        for r in self.retries(timeout):
            with r:
                customer_info = self.default_admin_client.customer.get(customer_id)
                self.assertIsNotNone(customer_info['os_tenant_id'], 'Tenant for user {} is not created after {} seconds'.format(
                                     customer_info['detailed_info']['name'], timeout))
        return customer_info

    @classmethod
    def check_horizon(cls, client: CabinetBackendClient):
        """Check horizon access for passed client."""
        client.send_command_get('/api/config.js')
        config = client.last.text
        horizon_url = re.search(r'"horizon_url": "(?P<horizon_url>.+?)"', config).group('horizon_url')
        dashboard_url = posixpath.join(horizon_url, 'project/')
        raw = client.session.get(dashboard_url)
        if re.search(r'<form.+?ng-controller="hzLoginCtrl".+?action="/horizon/auth/login/".+?>', raw.text, re.DOTALL):
            raw.status_code = 401
            raise HTTPError('Not authorized in openstack dashboard', response=raw)
        return raw

    def get_default_admin_credentials(self):
        """Return default admin credentials."""
        return configs.default_admin

    @classmethod
    def get_default_promocode(cls):
        """Return first valid promocode."""
        if configs.promocodes.promo_registration_only:
            for promo, expdate in configs.promocodes.codes.items():
                if expdate > datetime.date.today():
                    return promo
            raise ValueError('No valid promocode found. Promocodes: {}'.format(configs.promocodes.codes))

    @classmethod
    def get_immutable_services(cls):
        """Return generator over all immutable service id"""
        for service in cls.default_admin_client.service.list()['items']:
            if not service['mutable']:
                yield service['service_id']