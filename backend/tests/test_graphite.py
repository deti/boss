import conf
from tests.base import TestCaseApi, ResponseError
import mock
import requests
import posixpath


class TestGraphiteApi(TestCaseApi):

    def setUp(self):
        super().setUp()
        conf.statistics.graphite = 'http://example.com/'
        self.base_url = self.admin_client.graphite.url()

    @staticmethod
    def get_resp_mock():
        resp = mock.Mock()
        resp.headers = {}
        resp.body = bytes(0)
        resp.raw.data = bytes(0)
        resp.status_code = 200
        return resp

    @mock.patch('backend.api.admin.graphite.requests.request')
    def do_get(self, url_tail, mock_request):
        url = posixpath.join(self.base_url, url_tail)
        mock_request.return_value = self.get_resp_mock()
        raw_get_params = "?target=server.web1.load&height=800&width=600"
        self.admin_client.graphite.client.get(url + raw_get_params)
        mock_request.assert_called_once()
        ((req_method, req_url), kwargs) = mock_request.call_args
        self.assertEqual(req_method, 'GET')
        self.assertEqual(req_url, posixpath.join('http://example.com', url_tail))
        params = kwargs.get('params')
        self.assertIsNotNone(params)
        self.assertIn('target', params)
        self.assertIn('width', params)

    @mock.patch('backend.api.admin.graphite.requests.request')
    def do_post(self, url_tail, mock_request):
        url = posixpath.join(self.base_url, url_tail)
        mock_request.return_value = self.get_resp_mock()
        post_params = {
            'target': 'server.web1.load',
            'height': 800,
            'width': 600
        }
        list_post_params = list(post_params.items())
        list_post_params *= 2
        self.admin_client.app.post("/api/0/graphite/metrics/find/", params=list_post_params)

        self.admin_client.graphite.client.post(url, params=post_params)
        mock_request.assert_called_once()
        ((req_method, req_url), kwargs) = mock_request.call_args
        self.assertEqual(req_method, 'POST')
        self.assertEqual(req_url, posixpath.join('http://example.com', url_tail))
        data = kwargs.get('data')
        self.assertIsNotNone(data)
        self.assertIn(b'target', data)
        self.assertIn(b'width', data)

    def do_test_request(self, url):
        self.do_get(url)
        self.do_post(url)

    def test_render(self):
        self.do_test_request('render/')

    def test_metrics_find(self):
        self.do_test_request('metrics/find/')

    @mock.patch('backend.api.admin.graphite.requests.request')
    def test_error(self, mock_request):
        request_exception = requests.exceptions.RequestException('test')
        mock_request.side_effect = request_exception
        with self.assertRaises(ResponseError):
            self.admin_client.graphite.client.get(self.base_url)

    @mock.patch('backend.api.admin.graphite.requests.request')
    def test_http_error(self, mock_request):
        http_error = requests.exceptions.HTTPError("test")
        resp = self.get_resp_mock()
        resp.raise_for_status.side_effect = http_error
        mock_request.return_value = resp
        with self.assertRaises(ResponseError):
            self.admin_client.graphite.client.get(self.base_url)
