import bottle
import inspect
import threading
import conf
from posixpath import join
from bottle import request, HTTPResponse, response as bottle_response
from functools import wraps


local_properties = threading.local()

API_CABINET = "API_CABINET"
API_ADMIN = "API_ADMIN"
API_ALL = "API_ALL"

ADMIN_PREFIX = "/api/"
LK_PREFIX = "/lk_api/"

ADMIN_TOKEN_NAME = "token"
CABINET_TOKEN_NAME = "cabinet_token"


def request_api_type():
    if request.path.startswith(ADMIN_PREFIX):
        return API_ADMIN
    if request.path.startswith(LK_PREFIX):
        return API_CABINET
    raise Exception("Unknown prefix of request path %s" % request.path)


class Api(object):
    version = 0
    api_type = None
    api_prefix = ""

    @staticmethod
    def paginated_list(pagination, short_display=False):
        from model import display
        return {"total": pagination.total, "page": pagination.page, "per_page": pagination.per_page,
                "items": display(pagination.items, short_display)}

    @staticmethod
    def set_cors_headers(response):
        response.set_header("Access-Control-Allow-Origin", bottle.request.get_header("Origin", "*"))
        response.set_header("Access-Control-Allow-Headers", "Content-Type, *")
        response.set_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        response.set_header("Access-Control-Allow-Credentials", "true")
        # This header is required by IE
        # http://msdn.microsoft.com/en-us/library/ms537343%28v=vs.85%29.aspx
        response.set_header("P3P", 'CP="CAO PSA CONi OTR OUR DEM ONL"')


def enable_cors(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            response = fn(*args, **kwargs)
            if isinstance(response, HTTPResponse):
                Api.set_cors_headers(response)
            else:
                Api.set_cors_headers(bottle_response)
            return response
        except HTTPResponse as error_response:
            Api.set_cors_headers(error_response)
            raise
    return wrapper


class AdminApi(Api):
    api_type = API_ADMIN


class CabinetApi(Api):
    api_type = API_CABINET


def request_base_url():
    entry_point = conf.backend.entry_point
    if entry_point:
        return entry_point
    url = request.urlparts
    return "{}://{}".format(url.scheme, url.netloc)


_registered = {}


def route(path, method, no_version=False, with_trailing_slash=True, internal=False, api_type=None):
    if with_trailing_slash:
        assert path.endswith('/'), "Path %s has to have trailing slash" % path

    def wrapper(f):
        assert path, "Path for {} cannot be empty!".format(f.__name__)

        if internal:
            if not conf.api.internal_methods_enabled:
                return f
            f._internal_api = True

        key = f.__module__, f.__name__
        path_for_same_name = _registered.get(key)
        if path_for_same_name:
            raise AssertionError(
                "Method '{}.{}' is already mapped to '{}'. New path - '{}'".format(
                    f.__module__, f.__name__, path_for_same_name, path)
            )
        _registered[key] = path

        if not hasattr(f, '_mapped_to'):
            f._mapped_to = {}
        # noinspection PyProtectedMember
        f._mapped_to[(method, path)] = (no_version, with_trailing_slash, api_type)
        return f

    return wrapper


def get(path, no_version=False, internal=False, api_type=None):
    return route(path, "GET", no_version, internal=internal, api_type=api_type)


def post(path, no_version=False, internal=False, api_type=None):
    return route(path, "POST", no_version, internal=internal, api_type=api_type)


def options(path, no_version=False, internal=False, api_type=None):
    return route(path, "OPTIONS", no_version, internal=internal, api_type=api_type)


def put(path, no_version=False, internal=False, api_type=None):
    return route(path, "PUT", no_version, internal=internal, api_type=api_type)


def delete(path, no_version=False, internal=False, api_type=None):
    return route(path, "DELETE", no_version, internal=internal, api_type=api_type)


def add_routes(app, obj, api_type):
    methods = inspect.getmembers(obj, inspect.ismethod)
    resources = (
        meth for name, meth in methods
        if hasattr(meth, '_mapped_to') and not name.startswith("_")
    )

    for resource in resources:
        for (method, path), (no_version, with_trailing_slash, method_api_type) in resource._mapped_to.items():
            if not method_api_type:
                method_api_type = resource.__self__.api_type
            if method_api_type != API_ALL and method_api_type != api_type:
                continue

            if method_api_type == API_ALL:
                method_api_type = api_type
            base_prefix = ADMIN_PREFIX if method_api_type == API_ADMIN else LK_PREFIX
            prefix = resource.__self__.api_prefix
            prefix = join(base_prefix, prefix)
            if not no_version:
                prefix = join(prefix, str(resource.__self__.version))

            path = join(prefix, path)

            if with_trailing_slash:
                path = path.rstrip("/")
                for p in (path, path + "/"):
                    app.route(p, method)(resource)
            else:
                app.route(path, method)(resource)
