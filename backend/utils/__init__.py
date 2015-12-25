# noinspection PyPep8Naming
import json
import logbook
import datetime
from decimal import Decimal
from functools import wraps
from contextlib import contextmanager


class cached_property(object):
    """ A property that is only computed once per instance and then replaces
        itself with an ordinary attribute. Deleting the attribute resets the
        property.
    """

    def __init__(self, func):
        self.func = func

    # noinspection PyUnusedLocal
    def __get__(self, obj, cls):
        if obj is None:
            return self
        value = obj.__dict__[self.func.__name__] = self.func(obj)
        return value


class DateTimeJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        from utils.money import decimal_to_string
        if isinstance(obj, datetime.datetime):
            from pytz import utc
            obj = obj.replace(microsecond=0, tzinfo=utc)
            return obj.isoformat()
        if isinstance(obj, datetime.date):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return decimal_to_string(obj)
        elif hasattr(obj, "to_json"):
            return obj.to_json()
        else:
            return super(DateTimeJSONEncoder, self).default(obj)


def handle_exception(exit_on_error=False):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # noinspection PyBroadException
            try:
                return fn(*args, **kwargs)
            except Exception:
                import traceback
                import _thread
                logbook.warning(u"Traceback: {}".format(traceback.format_exc()))
                exception_to_sentry()
                if exit_on_error:
                    traceback.print_exc()
                    _thread.interrupt_main()
                return None
        return wrapper
    return decorator


def exception_to_sentry(extra=None):
    import conf
    import traceback
    from raven import Client

    if conf.test or conf.region.lower() == "local" or not conf.sentry.backend:
        traceback.print_exc()
        logbook.exception("")
        return
    data = {
        "version": getattr(conf, "version", None)
    }
    data.update(extra or {})

    client = Client(conf.sentry.backend)
    client.captureException(extra=data, tags=conf.logging.handlers.Sentry.tags)


def utc_hour():
    """
    Return current datetime with zero minutes and seconds
    """
    return datetime.datetime.utcnow().replace(minute=0, second=0, microsecond=0)


def day_start(timestamp, hour=0):
    return timestamp.replace(minute=0, second=0, microsecond=0, hour=hour)


def find_first(seq, predicate):
    return next((x for x in seq if predicate(x)), None)


def setup_backend_logbook(app_name, sql_log=None, openstack_log_level=None, min_level=None):
    import logging
    import conf
    from lib.logger import setup_logbook, redirect_logging

    setup = setup_logbook(app_name, conf.logging, min_level)
    if sql_log is None:
        sql_log = conf.devel.sql_log

    if sql_log:
        logger = logging.getLogger('sqlalchemy.engine')
        redirect_logging(logger)

    for logger_name in ('keystoneclient', 'ceilometerclient', 'cinderclient',
                        'glanceclient', 'neutronclient', 'novaclient', 'celery'):
        logger = logging.getLogger(logger_name)
        logger.setLevel(openstack_log_level or conf.openstack.loglevel)
        redirect_logging(logger)

    return setup


def find_first(seq, predicate):
    return next((x for x in seq if predicate(x)), None)


def setup_console_logbook(level="DEBUG", sql_log=False, openstack_level=False, app_name="stderr"):
    # This function is used for simple enabling logging in python/ipython console
    import conf
    conf.devel.sql_log = sql_log
    handlers = conf.logging["handlers"]
    handlers[app_name]["level"] = level

    handler = setup_backend_logbook(app_name, sql_log, openstack_level)
    handler.push_application()


def make_content_disposition(filename, user_agent=None):
    import re
    from urllib.parse import quote

    filename = filename.encode("utf-8")
    older_msie_pattern = r"^.*MSIE ([0-8]{1,}[\.0-9]{0,}).*$"
    safari_pattern = r"^.*AppleWebKit.*$"
    user_agent = user_agent or ""

    if re.match(older_msie_pattern, user_agent, re.IGNORECASE):
        return "attachment;filename={}".format(quote(filename))
    elif re.match(safari_pattern, user_agent, re.IGNORECASE):
        return "attachment;filename={}".format("".join(map(chr, filename)))
    return "attachment;filename*=utf-8''{}".format(quote(filename))


def grouped(iterable, n):
    from itertools import zip_longest
    """s -> (s0,s1,s2,...sn-1), (sn,sn+1,sn+2,...s2n-1), (s2n,s2n+1,s2n+2,...s3n-1), ..."""
    return zip_longest(*[iter(iterable)] * n)


@contextmanager
def timed(description, debug_level=True):
    start = datetime.datetime.utcnow()
    yield
    end = datetime.datetime.utcnow()
    log_func = logbook.debug if debug_level else logbook.info
    log_func("time of {}: {}", description, end - start)
