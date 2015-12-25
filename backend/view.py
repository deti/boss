"""
Runs debug server with API and frontend for local development

Usage:
    backend [options]

Options:
  -h --help                 Show this screen.
  --host=HOST               Host for the backend [default: localhost]
  -p --port=PORT            Port for the backend [default: 8080]
  --jsdir=DIR               Directory for compiled frontends [default: build]


Use $ bin/backend then open http://127.0.0.1:8080/admin/ or run some API tests against it
"""
import conf
import bottle
import logbook
import os
from api import add_routes, API_ALL, API_ADMIN, API_CABINET, local_properties
from bottle import HTTPResponse, HTTPError
from utils import coverage_report
from lib import root_directory

# Monkey-patch content-length limit
from plugins.request_log import RequestLogPlugin

bottle.BaseRequest.MEMFILE_MAX = conf.api.memfile_max


def get_error_handler(application):
    def default_error_handler(error):
        if isinstance(error, HTTPError):
            r = HTTPResponse()
            error.apply(r)
            r.content_type = error.content_type
            return r
        return error

    return default_error_handler


def api_handler(api_type):
    import conf
    from api.utility import UtilityApi
    from api.admin.user import UserApi
    from api.admin.service import ServiceApi
    from api.cabinet.customer import CustomerApi
    from api.admin.tariff import TariffApi
    from api.admin.currency import CurrencyApi
    from api.admin.news import NewsApi
    from api.admin.payments import PaymentsApi
    from api.admin.report import ReportApi
    from utils import setup_backend_logbook
    from api.admin.graphite import GraphiteApi

    if not conf.test:
        handler = setup_backend_logbook("backend_admin")
        handler.push_application()

    application = bottle.Bottle(autojson=False)

    for api in [UtilityApi(), UserApi(), ServiceApi(), CustomerApi(), TariffApi(), CurrencyApi(),
                NewsApi(), PaymentsApi(), ReportApi(), GraphiteApi()]:
        if api_type == API_ALL:  # use both internal and external methods
            add_routes(application, api, API_ADMIN)
            add_routes(application, api, API_CABINET)
        else:
            add_routes(application, api, api_type)

    # logbook.debug("Allowed methods: {}", "\n".join(["%s %s" % (r.method, r.rule) for r in application.routes]))

    application.default_error_handler = get_error_handler(application)

    application.install(RequestLogPlugin(conf.api.request_id_size, local_properties, conf.devel.debug, conf.test))

    return application


def _add_local_static_routes_for_development_server(application, js="build"):
    admin_path = os.path.join(root_directory(), "frontend", "admin", "apps", "data-pro-admin", js, "admin")
    lk_path = os.path.join(root_directory(), "frontend", "lk", "apps", "data-pro", js, "lk")

    @application.route("/admin")
    @application.route("/admin/")
    @application.route("/admin/<path:path>")
    def admin_index(path=None):
        if path is None:
            path = "index.html"
        local_path = os.path.join(admin_path, path)
        if not os.path.isfile(local_path):
            path = "index.html"

        return bottle.static_file(path, admin_path)

    @application.route("/lk")
    @application.route("/lk/")
    @application.route("/lk/<path:path>")
    def lk_index(path=None):
        if path is None:
            path = "index.html"
        local_path = os.path.join(lk_path, path)
        if not os.path.isfile(local_path):
            path = "index.html"

        return bottle.static_file(path, lk_path)

    @application.route("/favicon.ico")
    def favicon():
        return bottle.static_file("assets/favicon.ico", lk_path)

    @application.route("/")
    def lk_redirect():
        return bottle.redirect("/lk/")


def main():
    import docopt
    opt = docopt.docopt(__doc__)

    if conf.devel.coverage_enable:
        coverage_report.coverage_on_start(conf.devel.coverage)

    application = api_handler(API_ALL)
    _add_local_static_routes_for_development_server(application, js=opt["--jsdir"])

    import signal
    signal.signal(signal.SIGINT, lambda s, f: exit())

    logbook.info("Start backend on host {}:{}", opt["--host"], opt["--port"])
    bottle.run(app=application, host=opt["--host"], port=int(opt["--port"]),
               debug=conf.devel.debug, reloader=False)


def cabinet_api_handler():
    return api_handler(API_CABINET)


def admin_api_handler():
    return api_handler(API_ADMIN)


def all_api_handler():
    return api_handler(API_ALL)

if __name__ == '__main__':
    main()
