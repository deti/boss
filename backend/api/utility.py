# -*- coding: utf-8 -*-
import bottle
import json
import conf
import logbook
import re
import errors

from bottle import Response, response
from api import Api, get, delete, route, API_ALL, API_ADMIN, post, request_api_type, enable_cors
from api.check_params import check_params
from api.validator import String, List, Choose, Regexp, TokenId, Email, EmailList
from api.admin.role import TokenAdmin
from model import User, autocommit, Customer, Tariff, News, Service, MessageTemplate
from model.account.role import Role
from utils.i18n import all_languages, available_languages, all_locales, preferred_language
from task.mail import send_email
from lib import version, build_id

TIMEZONES = []


# noinspection PyMethodMayBeStatic
class UtilityApi(Api):
    api_type = API_ADMIN

    @get("version/", no_version=True, api_type=API_ALL)
    def get_version(self):
        """
        Returns current code version

        :return str version: Release version
        :return str region: backend region
        :return str availability_zone: backend availability_zone
        :return str api_version: supported api version

                Example::

                    {
                        region: "az1",
                        version: {
                            date: "2013-10-15_20-52-33",
                            release: "dev",
                            build: 509
                        },
                        stage: "dev"
                    }
        """

        build = build_id()
        return {"version": version("backend"), "api_version": 0,
                "region": conf.region, "availability_zone": conf.availability_zone,
                "date": build["date"], "build_id": build["build"]}

    @get("check_exception/", no_version=True)
    @check_params(text=String)
    def check_exception(self, text="Check sentry exception"):
        """
        **Service method**, it raise exception to be sure that sentry and log system is configured as expected
        """
        logbook.error("check error message in check_exception: {}", text)
        raise Exception(text)

    # # noinspection PyUnusedLocal
    # @get("/check_slow_request/", no_version=True, internal=True)
    # @check_params(text=String)
    # def check_slow_request(self, text="Check sentry exception"):
    #     """
    #     **Utility method** for checking slow requests
    #     """
    #     import time
    #     timeout = (conf.profiling.only_slower_than or 0) + 0.5
    #     time.sleep(timeout)
    #     return {"seconds": timeout}
    #
    # # noinspection PyUnresolvedReferences

    deletable_tables = {"user": User, "customer": Customer, "tariff": Tariff,
                        "news": News, "service": Service}

    @delete("_force_delete/", internal=True, api_type=API_ALL)
    @check_params(token=TokenAdmin, tables=List(Choose(list(deletable_tables.keys()))),
                  prefix=Regexp(re.escape(conf.devel.test_prefix)),
                  field=String)
    @autocommit
    def force_delete(self, tables, prefix, field=None):
        """
        **Service method**. It removes objects from db. **Only tests should use it!**

        :param Table[] tables: List of tables for cleanup
        :param Field field: This field is used for filtering. For example name or email.
                            By default the unique index of table is used
        :param str prefix: Prefix for object removing
        """
        result = {}
        for table in tables:
            logbook.info("Force removing objects from {} with prefix {}", table, prefix)
            count = self.deletable_tables[table].delete_by_prefix(prefix, field)
            result[table] = count
        return {"deleted": result}

    @post('send_email/', api_type=API_ADMIN)
    @check_params(token=TokenId, send_to=Email, send_cc=EmailList,
                  subject=String)
    def send_email(self, send_to, send_cc=None, subject=None):
        """
        Send email to specified email send_to with custom subject and body.

        :param Email send_to: email to send message to.
        :param list send_cc: list of emails for cc email field.
        :param str subject: custom subject for email.
        """
        template_subject, body = MessageTemplate.get_rendered_message(MessageTemplate.SEND_EMAIL,
                                                                      language=preferred_language())
        if subject is None:
            subject = template_subject
        send_email.delay(send_to, subject, body, cc=send_cc)
        return {}

    @route("config.js", "GET", no_version=True, with_trailing_slash=False)
    @enable_cors
    def get_config_js(self):
        """
        Return config for frontend

        **Example**::

            window.CONFIG = {
               "default_language": "en",
               "show_region_info": true,
               "sentry": "http://fabb17faa23840a78f84b1a6800678ec:a616079cb170@sentry.ru/2",
               "region": "dev",
               "google_analytics":
                   {"admin": "UA-62743660-2", "lk": "UA-62743660-1"},
               "availability_zone": "local",
               "provider_info":
                   {"support_email": "support@hosting.com", "site_url": "hosting.com",
                    "support_phone": "+7 499 765-55-55"},
               "support_subjects": ["Финансовые вопросы", "Технические вопросы"],
               "recaptcha_site_key": "6LdBgwgTAAAAAIf7gim356DhVC6TlaV-Yg3xkPGc",
               "horizon_url": "http://boss.ru/horizon",
               "version": "0.1.1"
               }
        """
        provider = conf.provider.copy()
        if isinstance(provider["support_email"], list):
            provider["support_email"] = provider["support_email"][0]
        config = {
            "region": conf.region,
            "availability_zone": conf.availability_zone,
            "sentry": conf.sentry.js,
            "default_language": conf.ui.default_language,
            "show_region_info": conf.ui.show_region,
            "google_analytics": conf.ui.google_analytics,
            "support_subjects": conf.customer.support.subjects,
            "recaptcha_site_key": conf.api.secure.recaptcha.site_key,
            "provider_info": provider,
            "horizon_url": conf.openstack.horizon_url,
            "payments": {"cloudpayments": {"public_id": conf.payments.cloudpayments.public_id}},
            "offer_link": conf.ui.offer_link,
            "promo_registration_only": conf.promocodes.promo_registration_only,
            "test_period": conf.customer.test_customer.test_period.blocking,
            "version": version("frontend_admin") if request_api_type() == API_ADMIN else version("frontend_cabinet"),
            "skyline": conf.skyline
        }
        response.content_type = "application/x-javascript"
        return Response("window.CONFIG = {};".format(json.dumps(config)))

    @route("config.js", "OPTION", no_version=True, with_trailing_slash=False)
    @enable_cors
    def login_option(self):
        r = bottle.HTTPResponse("")
        r.content_type = "text/html"
        return r

    @get("role/")
    def role_list(self):
        """
           Returns list of roles with internalization

           **Example**::

                {"roles":
                    [{"role_id": "manager", "localized_name": {"ru": "Менеджер", "en": "Manager"}},
                     {"role_id": "support", "localized_name": {"ru": "Поддежрка", "en": "Support"}},
                     {"role_id": "account", "localized_name": {"ru": "Бизнес Менеджер", "en": "Business Manager"}},
                     {"role_id": "admin",   "localized_name": {"ru": "Админ", "en": "Admin"}}}
                }
        """

        roles = [Role.display(role) for role in Role.ROLE_LIST]
        return {"roles": roles}

    @staticmethod
    def _prepare_country_description(code, desc):
        return {"code": code, "localized_name": desc}

    @get("country/")
    def country_list(self):
        """
        Return list of countries with internationalization

        :return List countries: list of countries with internationalization

       **Example**::

            {"countries":
                [{"code": "BN", "localized_name": {"en": "Brunei Darussalam", ru: "Бруней-Даруссалам"}},
                 {"code": "AN", "localized_name": {"en": "Netherlands Antilles",
                                                   "ru": "Нидерландские Антильские острова"}}]
            }
        """
        countries = [self._prepare_country_description(code, desc)
                     for code, desc in conf.country.all.items()]
        return {"countries": countries}

    @staticmethod
    def _prepare_subscription_description(name, desc):
        return {"name": name, "localized_description": desc}

    @get("subscription/")
    def subscription_list(self):
        """
        Return list of subscriptions with internationalization

        :return List subscriptions: list of subscriptions with internationalization

       **Example**::

            {"subscriptions":
                [{"name": "news",
                    "localized_description":
                        {"en": "Subscribe to announcements of special offers, new tariffs and services.",
                         "ru": "Рассылка анонсов о спецакциях, новых тарифах и услугах компании."}
                 {"name": "billing",
                    "localized_description":
                        {"en": "Notifications on cash flow on your account (debiting and replenishment).",
                         "ru": "Рассылка уведомлений об угрозе блокирования аккаунта, о блокировке и разблокировке."}}]
            }
        """
        return {"subscriptions": [self._prepare_subscription_description(name, desc)
                                  for name, desc in conf.subscription.items()]}

    @staticmethod
    def _prepare_quota_description(template_name, template):
        template_info = []
        for name, value in template.items():
            template_info.append({
                "limit_id": name,
                "localized_description": conf.quotas.all[name].get("localized_description", {}),
                "localized_name": conf.quotas.all[name].get("localized_name", {}),
                "localized_measure": conf.quotas.all[name].get("localized_measure", {}),
                "value": value
            })
        return {"template_id": template_name,
                "template_info": template_info}

    @get('quotas/templates/')
    @check_params(token=TokenId)
    def quotas_templates_list(self):
        """
        Get description of quotas templates

        :return list quotas_templates: Returns list of dicts with all quotas templates information.

        **Example**::

            {
                "quotas_templates": [
                    {
                        "template_id": "test_customer",
                        "template_info": [{
                            "limit_id": "fixed_ips",
                            "localized_description": {
                                "en": "The maximum number of fixed IPs (private IPs) for the project.",
                                "ru": "Максимальное количество внутренних IP адресов (fixed_ip), всего на тенант."
                            },
                            "localized_name": {
                                "en": "Private IPs",
                                "ru": "Внетренние IP"
                            },
                            "localized_measure": {
                                "en": "pcs.",
                                "ru": "шт."
                            },
                            "value": 128
                        }, {...}]
                    },
                    {...}
                ]
            }
        """
        return {"quotas_templates": [self._prepare_quota_description(k, v)
                                     for k, v in conf.template.items() if k != 'all']}

    @get("language/", api_type=API_ALL)
    def get_languages(self):
        """
        Return list of all languages

        :return language_list: List of languages.

        **Example**::

            {
                "language_list": {
                    "ru": {
                        "ru": "\u0420\u0443\u0441\u0441\u043a\u0438\u0439",
                        "en": "Russian"
                    },
                    "en": {
                        "ru": "\u0410\u043d\u0433\u043b\u0438\u0439\u0441\u043a\u0438\u0439",
                        "en": "English"
                    },
                    "gv": {
                        "ru": "\u041c\u044d\u043d\u0441\u043a\u0438\u0439",
                        "en": "Manx"
                    },
                    ...
                }
            }
        """
        return {"language_list": all_languages()}

    @get("language/active/", api_type=API_ALL)
    def get_active_languages(self):
        """
        Return list of active languages

        :return language_list: List of languages.

        **Example**::

            {
                "language_list": {
                    "ru": {
                        "ru": "\u0420\u0443\u0441\u0441\u043a\u0438\u0439",
                        "en": "Russian"
                    },
                    "en": {
                        "ru": "\u0410\u043d\u0433\u043b\u0438\u0439\u0441\u043a\u0438\u0439",
                        "en": "English"
                    }
                }
            }
        """
        return {"language_list": {l: all_languages()[l] for l in available_languages()}}

    # noinspection PyUnusedLocal
    @get("locale/active/", api_type=API_ALL)
    def get_active_locales(self):
        """
        Returns list of active locales.

        :return List locale_list: List of locales.

        **Example**::

            {
                "locale_list": {
                    "ru": {
                        "ru": "\u0420\u0443\u0441\u0441\u043a\u0438\u0439",
                        "en": "Russian"
                    },
                    "en": {
                        "ru": "\u0410\u043d\u0433\u043b\u0438\u0439\u0441\u043a\u0438\u0439",
                        "en": "English"
                    },
                    "en_CA": {
                        "ru": "\u041a\u0430\u043d\u0430\u0434\u0441\u043a\u0438\u0439...",
                        "en": "Canadian English"
                    },
                    "en_AU": {
                        "ru": "\u0410\u0432\u0441\u0442\u0440\u0430\u043b\u0438\u0439\u0441\u043a\u0438\u0439 ...",
                        "en": "Australian English"
                    },
                    "en_US": {
                        "ru": "\u0410\u043c\u0435\u0440\u0438\u043a\u0430\u043d\u0441\u043a\u0438\u0439...",
                        "en": "U.S. English"
                    },
                    "en_GB": {
                        "ru": "\u0411\u0440\u0438\u0442\u0430\u043d\u0441\u043a\u0438\u0439...",
                        "en": "British English"
                    }
                }
            }
        """
        locales = all_locales()
        languages = available_languages()
        enabled_locales = {code: name for code, name in locales.items()
                           if code.split("_", 1)[0] in languages}
        return {"locale_list": enabled_locales}

    @get("event/<event>/allowed_period/", api_type=API_ALL)
    def allowed_period(self, event):
        """
        Returns list of allowed periods for events.

        :param str event: Type of event.  Currently supported: auto_report
        :return List periods: List of periods.

        **Example**::

            {
              "periods": [
                            {'period_id': 'week', 'localized_name': {'ru': 'еженедельно', 'en': 'weekly'}},
                            {'period_id': 'month', 'localized_name': {'ru': 'ежемесячно', 'en': 'monthly'}},
                            {'period_id': 'quarter', 'localized_name': {'ru': 'ежеквартально', 'en': 'quarterly'}}
                         ]
            }
        """

        event_config = conf.event.event.get(event)
        if not event_config:
            raise errors.NotFound()
        periods = event_config["periods"]

        def copy_except(d, exclude):
            return {k: v for k, v in d.items() if k not in exclude}
        return {"periods": [{"period_id": period,
                             "localized_name": copy_except(conf.event.period[period], "cron")} for period in periods]}

    @get("health/")
    def services_health(self):
        """
        Checks health of services: db, redis, openstack

        :return dict health: dict with services states

        **Example**::

            {
                "health": {
                    "db_write": true,
                    "db_read": false,
                    "redis_read": true,
                    "redis_write": false,
                    "openstack_api": true
                }
            }

        """
        from utils.check_config import check_config
        resp = {name: not bool(error) for name, error in check_config().items()}
        return {'health': resp}
