# -*- coding: utf-8 -*-
import logbook
import os

from logbook.compat import RedirectLoggingHandler
from raven.handlers.logbook import SentryHandler as _SentryHandler


class SentryHandler(_SentryHandler):
    # noinspection PyUnusedLocal
    def __init__(self, dsn, format_string=None, tags=None, timeout=None, **kwargs):
        from raven.base import Client
        self.tags = tags
        client = Client(dsn=dsn, timeout=timeout, tags=tags)
        # hack raven because it ignore timeout parameter

        super().__init__(client, **kwargs)


logbook.SentryHandler = SentryHandler


def _replace_config(config, pattern, new):
    for key, value in config.items():
        if isinstance(value, str) and value.find(pattern) >= 0:
            config[key] = value.replace(pattern, new)


# noinspection PyUnusedLocal
def only_api_filter(record, handler):
    return record.extra["api"]


# noinspection PyUnusedLocal
def without_api_filter(record, handler):
    return not record.extra["api"]


def redirect_logging(logger):
    del logger.handlers[:]
    logger.addHandler(RedirectLoggingHandler())


def setup_logbook(app_name, config, min_level=None):
    if not config.syslog:
        try:
            os.makedirs(config.log_dir)
        except OSError:
            pass

    app_config = config.applications[app_name] or {}
    handlers = app_config.get("handlers") or config.default.handler_list
    logbook_handlers = []

    finger_cross_config = config.finger_cross.copy()
    top_handler = True
    if min_level:
        min_level = logbook.lookup_level(min_level)

    for handler_name in handlers:
        handler_config = config.handlers[handler_name].copy()
        level = handler_config.get("level")
        if min_level and level:
            level = logbook.lookup_level(level)
            handler_config["level"] = max(min_level, level)
        handler_class = getattr(logbook, handler_config.pop("type"))
        finger_cross = handler_config.pop("finger_cross", False)
        _replace_config(handler_config, "__APP__", app_name)
        if "format_string" not in handler_config and handler_class is not logbook.NullHandler:
            handler_config["format_string"] = config.default.format_string

        if top_handler:
            handler_config["bubble"] = False

        if "filter" in handler_config:
            handler_config["filter"] = globals()[handler_config["filter"]]
        handler = handler_class(**handler_config)
        if finger_cross:
            finger_cross_level = logbook.lookup_level(finger_cross_config.pop("action_level"))
            handler = logbook.FingersCrossedHandler(handler, action_level=finger_cross_level, **finger_cross_config)
        logbook_handlers.append(handler)
        top_handler = False

    setup = logbook.NestedSetup(logbook_handlers)
    return setup
