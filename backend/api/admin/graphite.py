import conf
import io
import posixpath
import requests
import logbook
from requests.exceptions import RequestException
from api import AdminApi, get, post
from bottle import request, HTTPResponse
from errors import NotFound, ServiceUnavailable


class GraphiteApi(AdminApi):
    """
    NOTES: Graphit supports POST requests as well
    https://github.com/graphite-project/graphite-web/issues/591
    """

    hopbyhop_headers = ['connection', 'keep-alive', 'public',
                        'proxy-authenticate', 'transfer-encoding', 'upgrade']

    @property
    def entry_point(self):
        result = conf.statistics.graphite
        return result

    @get("graphite/render/")
    def render_get(self):
        return self.passthough('GET', 'render/')

    @post("graphite/render/")
    def render_post(self):
        return self.passthough('POST', 'render/')

    @get("graphite/metrics/find/")
    def metrics_find_get(self):
        return self.passthough('GET', 'metrics/find/')

    @post("graphite/metrics/find/")
    def metrics_find_post(self):
        return self.passthough('POST', 'metrics/find/')

    def passthough(self, method, url):
        assert(method in ('GET', 'POST'))
        if self.entry_point is None:
            raise NotFound()
        url = posixpath.join(self.entry_point, url)
        request_params = '; '.join([k + '=' + (','.join(request.params.getall(k)))
                                   for k in request.params.keys()])

        logbook.debug("[graphite] Request: {} with {}.", url, request_params)
        request.body.seek(0)
        body = request.body.read()
        logbook.debug("Request query: {}", request.query_string)
        logbook.debug("Request body: {}", body)

        headers = dict(request.headers)
        if method == "GET":
            headers.pop("Content-Length", None)
        logbook.debug("Request headers: {}", headers)
        try:
            resp = requests.request(method, url, params=request.query_string, data=body,
                                    stream=True, headers=headers)
        except RequestException as err:
            logbook.error("[graphite] Request exception: {}. Url: {}. Params: {}",
                          err, url, request_params)
            raise ServiceUnavailable(str(err))

        headers = {k: v for (k, v) in resp.headers.items()
                   if k.lower() not in self.hopbyhop_headers}
        return HTTPResponse(resp.raw.data, status=resp.status_code, headers=headers)
