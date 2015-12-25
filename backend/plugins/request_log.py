# -*- coding: utf-8 -*-
import conf
import random
import string
import json

import logbook
import bottle

import time
from lib import exception_safe
from utils import DateTimeJSONEncoder
from sqlalchemy.exc import OperationalError


# noinspection PyMethodMayBeStatic
class RequestLogPlugin(object):
    """ This plugin passes add request_id to logbook records"""

    name = 'request_id'
    api = 2
    chars = string.ascii_uppercase + string.digits + string.ascii_lowercase
    excluded_parameters = frozenset(["password"])
    parameters_log_limit = 100

    def __init__(self, size, local_properties, debug=False, under_test=False):
        self.size = size
        self.local_properties = local_properties
        self.debug = debug
        self.under_test = under_test

    def generate_id(self):
        return "".join(random.choice(self.chars) for _ in range(self.size))

    @staticmethod
    def get_client_address():
        try:
            return bottle.request.environ['HTTP_X_FORWARDED_FOR'].split(',')[0].strip()
        except KeyError:
            return bottle.request.environ.get('REMOTE_ADDR', '')

    def extract_user(self):
        user_token = getattr(self.local_properties, 'user_token', None)
        if not user_token:
            return "", "", ""

        tokenid, role, email = user_token.id, user_token.role, user_token.email
        delattr(self.local_properties, 'user_token')
        return tokenid, role, email

    @staticmethod
    def prepare_parameters(params, valid_encoding):
        exception_words = [
            'password',
        ]
        mask_symbols = '*' * 8

        def fix_encode(value):
            if valid_encoding:
                return value
            try:
                if isinstance(value, bytes):
                    return value.decode("utf-8")
                elif isinstance(value, str):
                    return value.encode('latin1').decode("utf-8")
                return value
            except (UnicodeDecodeError, UnicodeEncodeError) as e:
                try:
                    safe_encoded = value.encode("ascii", "backslashreplace").decode("ascii")
                except Exception:
                    safe_encoded = "<not printable>"

                logbook.warning("Can't decode type {} '{}': {}", type(value), safe_encoded, e)
                return value.encode("ascii", "backslashreplace").decode("ascii")

        result = ["(%s=%s)" % (fix_encode(k), fix_encode(v) if k not in exception_words else mask_symbols)
                  for k, v in params.items()]

        return ",".join(result)

    def post_to_str(self, request):
        is_json = True
        try:
            parameters = request.json
        except ValueError:
            parameters = None

        if parameters is None:
            is_json = False
            parameters = request.POST
        return self.prepare_parameters(parameters, is_json)

    @exception_safe
    def request_str(self, short=False):
        ip = self.get_client_address()
        gets = self.prepare_parameters(bottle.request.GET, False)
        if len(gets) > self.parameters_log_limit:
            gets = gets[:self.parameters_log_limit - 3] + "..."
        posts = self.post_to_str(bottle.request)

        if short:
            user_parameters = list(self.extract_user())

            parameters = user_parameters + [
                bottle.request.method,
                bottle.request.path,
                gets,
                posts,
            ]
        else:
            parameters = [
                ip,
                str(bottle.request.get_cookie("token", "")),
                bottle.request.method,
                bottle.request.path,
                gets,
                posts,
            ]
        return "|".join(parameters)

    @exception_safe
    def response_process(self, response, work_time):
        if response is None:
            logbook.error("Response can't be None")
            response = body_to_log = "{}"
            status = 200

        elif isinstance(response, bottle.Response):
            if response.content_type.startswith("text/") or response.content_type == "application/json":
                body_to_log = str(response.body) or getattr(response, "message", "")
            else:
                body_to_log = response.content_type
            status = response.status

        elif isinstance(response, dict):
            status = 200

            try:
                body_to_log = json.dumps(response, cls=DateTimeJSONEncoder)
                if self.debug:
                    response = json.dumps(response, cls=DateTimeJSONEncoder, indent=4)
                else:
                    response = body_to_log
            except TypeError:
                logbook.exception("Can't encode reply: {}", response)
                raise bottle.HTTPError(body="Internal Server Error")

            bottle.response.content_type = 'application/json'
        else:
            logbook.error("Incorrect response ({}): {}", type(response), response)
            body_to_log = str(response)
            status = 200
        self.log_response(body_to_log, status, work_time)
        return response

    def log_response(self, response_body, status, work_time):
        from io import BufferedReader
        if isinstance(work_time, float):
            work_time = "%.2f" % work_time
        if isinstance(response_body, BufferedReader):
            response_body = "<BufferedReader>"
        response_parameters = [work_time, str(status), response_body]
        log_response = self.request_str(short=True) + "|" + "|".join(response_parameters)
        logbook.notice(log_response, extra={"api": True})

    # noinspection PyUnusedLocal
    def apply(self, callback, context):
        import errors

        def wrapper(*args, **kwargs):
            start_time = time.time()
            request_id = self.generate_id()

            def inject_request_id(record):
                record.extra['request_id'] = request_id

            with logbook.Processor(inject_request_id):
                logbook.notice(self.request_str(), extra={"api": True})

                try:
                    response = callback(*args, **kwargs)
                except OperationalError as e:
                    logbook.warning("Database is down {}: {}", conf.database.uri, e, exc_info=True)
                    logbook.error("Database is down {}: {}", conf.database.uri, e)
                    response = errors.DatabaseIsDown()
                except errors.BadRequest as e:
                    e.format_response()
                    response = e
                except bottle.HTTPResponse as e:
                    response = e
                except Exception as e:
                    if self.under_test:
                        import traceback
                        traceback.print_exc()
                    logbook.exception("Exception during processing request: %s %s" %
                                      (bottle.request.method, bottle.request.path))
                    self.log_response(str(e), 500, time.time() - start_time)
                    raise
                finally:
                    from model import db
                    db.session.remove()
                response = self.response_process(response, time.time() - start_time)

            return response
        return wrapper
