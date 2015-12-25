import imaplib
import posixpath
import base64
import re
import time
import requests
from requests.exceptions import SSLError
from light_tests.base import LightTestsBase
from light_tests.clients import backend
from light_tests.tools import TestError, skip_test
from contextlib import contextmanager


class LightTests(LightTestsBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.test_label:
            self.config['email_test']['subject'] += ' ' + self.test_label
        self.client = backend.AdminBackendClient(self.config['server_address'])
        if not self.openstack:
            LightTests.openstack_server_create = skip_test(LightTests.openstack_server_create)

    def handle_error(self, error):
        if isinstance(error, requests.HTTPError):
            print('Request url:', self.client.last.url)
            print('Request data:', self.client.last_data)
            print('Response content:', self.client.last.content)
        elif isinstance(error, SSLError):
            print('Request url:', self.client.last.url)
        return False

    @LightTestsBase.add_test
    def get_version(self):
        version = self.client.version()
        self.print('Backend version: {}'.format(version))

    @LightTestsBase.add_test
    def default_admin_logins(self):
        self.client.login(**self.config['default_admin'])
        self.print('Default admin login successful')

    @LightTestsBase.add_test
    def mysql_write(self):
        name = self.client.user_get()['user_info']['name']
        self.client.user_update(name)

    @LightTestsBase.add_test
    def get_role_list(self):
        role_list = self.client.role_list()['roles']
        if len(role_list) == 0:
            raise TestError('Empty role list')

    @LightTestsBase.add_test
    def tariff_list_not_empty(self):
        tariff_list = self.client.tariff_list()['tariff_list']['items']
        if len(tariff_list) == 0:
            raise TestError('Empty tariff list')
        self.print('Got {} tariffs'.format(len(tariff_list)))

    @LightTestsBase.add_test
    def default_tariff_exists(self):
        try:
            default_tariff = self.client.tariff_get_default()['tariff_info']
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                raise TestError('Default tariff not found')
            raise
        self.print('Got default tariff: {}'.format(default_tariff['localized_name']['en']))

    @contextmanager
    def construct_imap(self, host, login, password, use_ssl:bool) -> imaplib.IMAP4:
        if use_ssl:
            imap = imaplib.IMAP4_SSL(host)
        else:
            imap = imaplib.IMAP4(host)
        imap.login(login, password)
        imap.select()
        try:
            yield imap
        finally:
            imap.close()
            imap.logout()

    def clear_emails(self, subject, credentials:dict):
        with self.construct_imap(**credentials) as imap:
            typ, data = imap.search(None, '(SUBJECT "{}")'.format(subject))
            emails = data[0].split()
            for num in emails:
                imap.store(num, '+FLAGS', '\\Deleted')
            imap.expunge()

    @LightTestsBase.add_test
    def send_test_email(self):
        credentials = self.config['email_test']['imap']

        self.clear_emails(self.config['email_test']['subject'], credentials)
        self.client.send_email(self.config['email_test']['email'], self.config['email_test']['subject'])

        start = time.time()

        for r in self.retries(self.config['email_test']['timeout'], sleep_time=1, exception=TestError):
            with r:
                with self.construct_imap(**credentials) as imap:
                    typ, data = imap.search(None, '(SUBJECT "{}" FROM "{}")'.format(
                        self.config['email_test']['subject'],
                        self.config['email_test']['from']))
                    emails = data[0].split()
                    if not emails:
                        raise TestError('Did not found email from {} with subject {} in {} seconds'.format(self.config['email_test']['from'],
                                                                                                           self.config['email_test']['subject'],
                                                                                                           self.config['email_test']['timeout']))
                    self.print('Found {} emails in {} seconds. Deleting...'.format(len(emails), round(time.time()-start, 2)))
                    for num in emails:
                        imap.store(num, '+FLAGS', '\\Deleted')
                    imap.expunge()

    def get_openstack_credentials(self) -> dict:
        credentials = self.config['openstack']['customer']['cabinet']
        self.print('Login in customer {email} with password {password}'.format(**credentials))
        customer_client = backend.CabinetBackendClient(self.config['server_address'])
        customer_info = customer_client.login(**credentials)['customer_info']
        self.print('Sending reset email...')
        credentials = self.config['openstack']['customer']['password_reset']
        subject = self.config['openstack']['customer']['subject']
        self.clear_emails(subject, credentials)
        customer_client.reset_os_password()
        self.print('Searching reset email...')
        for r in self.retries(120, sleep_time=1, exception=TestError):
            with r:
                with self.construct_imap(**credentials) as imap:
                    typ, data = imap.search(None, '(SUBJECT "{}")'.format(subject))
                    emails = data[0].split()
                    if len(emails) == 0:
                        raise TestError('No emails received matching subject="{}"'.format(subject))
                    email_id = emails[-1]
                    email_body = imap.fetch(email_id, '(UID BODY[TEXT])')[1][0][1].decode('utf-8')
                    email_body = email_body.split('\r\n\r\n')[1]
                    email_body = base64.b64decode(email_body).decode('utf-8')
                    match = re.search('OpenStack login: (?P<username>.+?)\s.*?'
                                      'OpenStack password: (?P<api_key>.+?)\s.*?'
                                      'OpenStack tenant: (?P<tenant_id>.+?)\s.*?'
                                      'OpenStack Keystone API: (?P<auth_url>.+?)\s', email_body, re.DOTALL)
                    if not match:
                        raise TestError('Email with credentials not found')
                    openstack_credentials = match.groupdict()
                    for num in emails:
                       imap.store(num, '+FLAGS', '\\Deleted')
                    imap.expunge()
                    self.print('Reset email found')
        return openstack_credentials

    def assertInList(self, seq, name:str, what:str):
        for item in seq:
            if item['name'] == name:
                return item
        else:
            raise TestError('{} "{}" not found in {} list:{}'.format(what.capitalize(), name, what, seq))

    @LightTestsBase.add_test
    def test_horizon_auth(self):
        customer_client = backend.CabinetBackendClient(self.config['server_address'])
        customer_client.login(**self.config['openstack']['customer']['cabinet'])['customer_info']
        customer_client.os_login()
        self.client.send_command_get('/api/config.js')
        config = self.client.last.text
        horizon_url = re.search(r'"horizon_url": "(?P<horizon_url>.+?)"', config).group('horizon_url')
        dashboard_url = posixpath.join(horizon_url, 'project/')
        raw = customer_client.session.get(dashboard_url)
        if re.search(r'<form.+?ng-controller="hzLoginCtrl".+?action="/horizon/auth/login/".+?>', raw.text, re.DOTALL):
            raw.status_code = 401
            raise TestError('Not authorized in openstack dashboard')
        return raw

    @LightTestsBase.add_test
    def openstack_server_create(self):
        from light_tests.clients.openstack import OpenstackClient

        openstack_client = OpenstackClient(**self.get_openstack_credentials())

        list_to_human = lambda l: list(map(lambda item: {'id': item.id, 'name': item.human_id}, l))

        flavor_name = self.config['openstack']['server']['flavor']
        flavor_list = list_to_human(openstack_client.list_flavor())
        flavor = self.assertInList(flavor_list, flavor_name, 'flavor')

        image_name = self.config['openstack']['server']['image']
        image_list = list_to_human(openstack_client.list_image())
        image = self.assertInList(image_list, image_name, 'image')

        network_name = self.config['openstack']['server']['network']
        network_list = openstack_client.list_network()['networks']
        network = self.assertInList(network_list, network_name, 'network')

        self.print('Creating server with name={name} image={image} flavor={flavor}'.format(
            **self.config['openstack']['server']))

        server = openstack_client.create_server(self.config['openstack']['server']['name'], image['id'], flavor['id'],
                                                nics=[{'net-id': network['id']}])

        self.print('Server created. Server id: {}'.format(server.id))
        try:
            for r in self.retries(120, exception=ValueError):
                with r:
                    data = openstack_client.nova_client.servers.get(server.id).to_dict()
                    vm_state = data['OS-EXT-STS:vm_state']
                    self.print('VM state:' + str(vm_state))
                    if vm_state != 'active':
                        if vm_state == 'error':
                            message = 'Error while creating server'
                            if 'fault' in data:
                                message += ': ' + data['fault']['message']
                            raise TestError(message)
                        raise ValueError('Server is not active yet.')
            self.print('Server is loaded.')
        finally:
            server.delete()
        self.print('Server deleted.')


def main() -> int:
    from light_tests.tools import _get_arguments
    args = _get_arguments()
    return LightTests(**args).run()


if __name__ == '__main__':
    exit(main())
