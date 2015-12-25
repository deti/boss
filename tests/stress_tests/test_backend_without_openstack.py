from contextlib import contextmanager
import json
import time
import threading
from urllib.parse import urljoin

import bottle
import logbook
import requests
from utils.base import BaseTestCase
import configs
import os


def route(route):
    def decorator(f):
        f.route = route
        return f
    return decorator


FILTER_HEADERS = ['connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization', 'te', 'trailers',
                  'transfer-encoding', 'upgrade']


class StoppableServer(bottle.ServerAdapter):
    server = None

    def run(self, handler):
        from wsgiref.simple_server import make_server
        self.server = make_server(self.host, self.port, handler, **self.options)
        self.server.serve_forever()

    def stop(self):
        self.server.shutdown()


class FakeOpenstack:
    thread = None
    server = None
    mock_raise = None
    service_mapping = dict()  # service name -> service public url
    timeout = 10.0
    patch_service_catalog = True

    def __init__(self):
        config = configs.read(os.environ['BOSS_CONFIG_REAL'], set_globals=False)
        self.auth_url = config['openstack']['auth']['auth_url']
        self.fake_auth_url = configs.openstack.auth.auth_url

        for kw in dir(self):
            attr = getattr(self, kw)
            if hasattr(attr, 'route'):
                bottle.route(attr.route, method=['GET', 'POST', 'PUT', 'DELETE'])(attr)

    @route('/v2.0/tokens')
    def tokens(self):
        """Handle auth requests, patch service catalog endpoint urls"""
        response = self.make_requests_request(bottle.request, urljoin(self.auth_url, 'tokens'))
        if response.status_code != 200 or not self.patch_service_catalog:
            logbook.info('Proxing tokens request to openstack without patching ({})', response.status_code)
            return self.make_bottle_response(response)
        try:
            parsed = response.json()
            for service_dict in parsed.get('access', {}).get('serviceCatalog', []):
                service_name = service_dict['name']
                endpoint = service_dict['endpoints'][0]
                for item in endpoint:
                    if item.endswith('URL'):
                        name = service_name+'_'+item[:-3]
                        self.service_mapping[name] = endpoint[item]  # e.g. nova_public, keystone_admin
                        endpoint[item] = self.urljoin(self.fake_auth_url, 'mock', name) + '/'
            dump = json.dumps(parsed)
        except Exception:
            logbook.exception('Error while patching service catalog')
            logbook.warning('Tokens content: {}', response.content)
            raise
        logbook.debug('service mapping is: {}', self.service_mapping)
        headers = self.filter_headers(response.headers)
        headers['Content-Length'] = len(dump)
        return bottle.HTTPResponse(dump, response.status_code, headers)

    @route('/v2.0/mock/<service>/<path:path>')
    def mock(self, service, path):
        """Handle requests to services. Proxy them to real urls or raise error."""
        if self.mock_raise is not None:
            raise bottle.HTTPError(self.mock_raise)
        if service not in self.service_mapping:
            logbook.warning('Requested unknown service: {} (mapping: {})', service, self.service_mapping)
            raise bottle.HTTPError(404, 'Unknown service')
        service_url = self.service_mapping[service]
        url = self.urljoin(service_url, path)
        if bottle.request.query:
            url += '?' + bottle.request.query_string
        return self.proxy_request(bottle.request, url)

    def urljoin(self, *args) -> str:
        full = args[0]
        for arg in args[1:]:
            if full.endswith('/') and arg.startswith('/'):
                full = full[:-1]
            elif not full.endswith('/') and not arg.startswith('/'):
                full += '/'
            full += arg
        return full

    @staticmethod
    def filter_headers(headers: dict) -> dict:
        """Remove invalid headers for WSGI response"""
        return {k: v for k, v in headers.items() if k.lower() not in FILTER_HEADERS}

    def make_bottle_response(self, requests_response:requests.Response) -> bottle.Response:
        """Create bottle response from requests response"""
        return bottle.HTTPResponse(requests_response.content, requests_response.status_code,
                                   self.filter_headers(requests_response.headers))

    def make_requests_request(self, bottle_request:bottle.Request, url) -> requests.Response:
        """Create and call requests request from bottle request"""
        headers = dict()
        for header, value in bottle_request.headers.items():
            if value:
                headers[header] = value
        method = bottle_request.method.lower()
        data = bottle_request.body.read()
        return getattr(requests, method)(url, headers=headers, data=data, timeout=self.timeout)

    def proxy_request(self, request:bottle.Request, url) -> bottle.Response:
        """Shortcut function"""
        return self.make_bottle_response(self.make_requests_request(request, url))

    def run(self):
        try:
            self.server = StoppableServer(**configs.fake_openstack)
            bottle.run(server=self.server)
        except:
            logbook.exception()
            raise

    def run_async(self):
        self.thread = threading.Thread(target=self.run)
        self.thread.start()
        time.sleep(10)

    @contextmanager
    def openstack_error_context(self, error_code:int):
        self.mock_raise = error_code
        logbook.warning('Enter error context: {}', error_code)
        try:
            yield
        finally:
            self.mock_raise = None
        logbook.warning('Exit error context: {}', error_code)


class TestBackendWithoutOpenstack(BaseTestCase):
    need_loggedin_client = False

    def setUp(self):
        super().setUp()
        self.fake_openstack = FakeOpenstack()
        self.fake_openstack.run_async()
        self.addCleanupAfterDelete(self.fake_openstack.server.stop)

    def test_customer(self):
        customer_info, _, customer_client = self.create_customer(True, with_client=True)

        with self.fake_openstack.openstack_error_context(503):
            self.default_admin_client.customer.update(customer_info['customer_id'], confirm_email=True)
            with self.assertRaises(AssertionError):
                self.wait_openstack(customer_info['customer_id'], 30)

        self.default_admin_client.customer.recreate_tenant(customer_info['customer_id'])
        self.wait_openstack(customer_info['customer_id'])
