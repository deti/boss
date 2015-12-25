import conf
import logbook
import errors
from babel.dates import format_datetime, format_date, format_time
from jinja2 import Template, TemplateSyntaxError, TemplateError, meta, Environment, StrictUndefined
from utils.i18n import _, localize_money
from arrow import utcnow
from functools import lru_cache


class Formatters(object):

    @classmethod
    def format(cls, formatter, language, data):
        assert hasattr(cls, formatter)
        return getattr(cls, formatter, cls.default_formatter)(language, data)

    @classmethod
    def default_formatter(cls, language, data):
        return data

    @staticmethod
    def money(language, data):
        return localize_money(language=language, **data)

    @staticmethod
    def datetime(language, datetime):
        return format_datetime(datetime=datetime, locale=language, format='full')

    @staticmethod
    def time(language, time):
        return format_time(time=time, locale=language)

    @staticmethod
    def date(language, date):
        return format_date(date=date, locale=language)


class MessageTemplate(object):
    SUBJECT = "subject"
    BODY = "body"
    VARIABLES = "variables"

    NEW_USER = "new_user"
    USER_PASSWORD_RESET = "user_password_reset"

    CUSTOMER_CONFIRMATION = "customer_confirmation"
    CUSTOMER_PASSWORD_RESET = "customer_password_reset"
    CUSTOMER_BLOCKED = "customer_blocked"
    CUSTOMER_BLOCKED_BY_MANAGER = "customer_blocked_by_manager"
    CUSTOMER_UNBLOCKED = "customer_unblocked"
    CUSTOMER_MAKE_PRODUCTION = "customer_make_production"
    CUSTOMER_BALANCE_LIMIT = "customer_balance_limit"
    CUSTOMER_HDD_DELETE = "customer_hdd_delete"
    CUSTOMER_WITHDRAW = "customer_withdraw"
    CUSTOMER_RECHARGE = "customer_recharge"
    CUSTOMER_RECHARGE_AUTO_REJECT = "customer_auto_recharge_reject"

    NEW_SERVICE_IN_TARIFF = "new_service_in_tariff"

    NEWS = "news"

    OS_CREDENTIALS = 'os_credentials'
    CUSTOMER_AUTO_REPORT = "customer_auto_report"

    SEND_EMAIL = 'send_email'


    @classmethod
    def _get_localized(cls, template_id, data_type, data_value, language):
        value = data_value.get(language)
        if value:
            return value

        logbook.error("{} from template {} not found for language {}", data_type, template_id, language)
        return data_value[conf.ui.default_language]

    @classmethod
    def get_template_data(cls, template_id, data_type, language):
        data_value = conf.message_template.templates[template_id][data_type]

        return cls._get_localized(template_id, data_type, data_value, language)

    @classmethod
    @lru_cache()
    def default_variables(cls):
        not_found = object()
        result = {}
        for variable_name, variable_data in conf.message_template.variables.items():
            if variable_data.get("default", not_found) != not_found:
                result[variable_name] = variable_data["default"]
        return result

    @classmethod
    def get_template_variables(cls, template_id):
        variables = frozenset(conf.message_template.templates[template_id][cls.VARIABLES] or []) | \
                    frozenset(cls.default_variables().keys())
        return variables

    @classmethod
    @lru_cache()
    def get_formatters(cls):
        result = {}
        for variable_name, variable_data in conf.message_template.variables.items():
            result[variable_name] = variable_data.get('formatter', 'default_formatter')
        return result

    @classmethod
    def _render(cls, text, context):
        try:
            env = Environment(undefined=StrictUndefined)
            ast = env.parse(text)
            unexpected = meta.find_undeclared_variables(ast) - context.keys()
            if unexpected:
                logbook.warning("Unexpected variables in template: {}. Context: {}, Template: {}",
                                ", ".join(unexpected), context, text)
                raise errors.MessageTemplateError(_("Unexpected variables in template: {}"), ", ".join(unexpected))
            template = Template(text, undefined=StrictUndefined)
            rendered = template.render(context)
            return rendered
        except TemplateSyntaxError as e:
            logbook.exception("Render template error: {}. Context: {}, template: {}", e.message, context, text)
            raise errors.MessageTemplateError(_("Template syntax error: {} at line {}.\nText: {}\nContext: {}"),
                                              e.message, e.lineno, text, context)
        except TemplateError as e:
            logbook.exception("Render template error: {}. Context: {}, template: {}, ", e, context, text)
            raise errors.MessageTemplateError(_("Error while rendering template: %s") % e.message)

    @classmethod
    def get_rendered_message(cls, template_id, language, **context):
        subject = cls.get_template_data(template_id, cls.SUBJECT, language)
        body = cls.get_template_data(template_id, cls.BODY, language)
        formatters = cls.get_formatters()

        new_context = dict(cls.default_variables())
        new_context.update(cls._context_defaults())
        for name, data in context.items():
            context[name] = Formatters.format(formatters[name], language, data)
        new_context.update(context)
        subject = cls._render(subject, new_context)
        body = cls._render(body, new_context)
        return subject, body

    @staticmethod
    def _context_defaults():
        time_now = utcnow()
        return {"current_date": time_now.date, "current_datetime": time_now.datetime}

