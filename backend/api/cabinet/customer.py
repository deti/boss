# -*- coding: utf-8 -*-
import bottle
import json
import logbook
import posixpath
import conf
import errors
from arrow import utcnow
from urllib.parse import urljoin
from api import (get, post, put, options, delete, CabinetApi, local_properties, request_base_url,
                 API_ADMIN, API_ALL, API_CABINET, request_api_type, CABINET_TOKEN_NAME, enable_cors)
from api.admin.currency import ActiveCurrencies
from api.admin.role import TokenManager, TokenAccount
from api.admin.tariff import TariffId, TariffIdExpand
from api.check_params import check_params
from api.validator import (Day, IndexSizeLimit, IntRange, Email, String, TokenId, CustomerTokenId, StringWithLimits,
                           Bool, ModelId, JSON, EmailList, ValidateError, DeferredDate, Integer, DecimalMoney, Date,
                           SecretSign, DateTime, ActiveLocale, Choose, PredefinedChoose, Visibility, PositiveInteger,
                           List, SortFields)
from model import Customer, autocommit, MessageTemplate, CustomerHistory, CustomerCard
from memdb.report_cache import ReportCache, CustomerReportId, ReportTask
from model import display, db, Deferred
from memdb.token import EmailConfirmationToken, CustomerToken, CustomerPasswordResetToken
from os_interfaces import horizon_wrapper
from os_interfaces.openstack_wrapper import openstack
from report import Report
from task.mail import send_email
from task.openstack import task_os_create_tenant_and_user, reset_user_password
from task.customer import report_file_generate
from utils import make_content_disposition
from utils.i18n import preferred_language, _
from datetime import timedelta
from service.payments import PaymentService


PasswordValidator = StringWithLimits(conf.customer.min_password_length, conf.customer.max_password_length)
WithdrawPeriod = Choose(list(conf.event.event.auto_report.periods.keys()))


TEMPLATE_VALIDATOR = Choose(list(conf.template))


class Subscribe(JSON):
    KEY_VALIDATOR = String()

    def __call__(self, value):
        if isinstance(value, str):
            parsed_value = super().__call__(value)
        else:
            parsed_value = value

        if not isinstance(parsed_value, dict):
            raise ValidateError(_("must be a dict"))
        try:
            subscriptions = {}
            for subscription_id, value in parsed_value.items():
                if subscription_id not in conf.subscription:
                    raise ValidateError(
                        _("subscription name must be one from list: {}"),
                        ",".join(map(str, conf.subscription.keys()))
                    )

                enable = Bool()(value['enable'])
                email = EmailList(', ')(value["email"])

                subscriptions[subscription_id] = {'enable': enable, 'email': email}
        except KeyError:
            raise ValidateError(_("Subscription can contain only 'enable' and 'email' keys"))
        return subscriptions


class QuotaValidator(JSON):
    def __call__(self, value):
        if isinstance(value, str):
            parsed_value = super().__call__(value)
        else:
            parsed_value = value

        if not isinstance(parsed_value, dict):
            raise ValidateError(_("must be a dict"))

        quotas = {}

        for name, value in parsed_value.items():
            if name not in conf.quotas.all:
                raise ValidateError(
                    _("quota name must be one from list: {}"),
                    ",".join(map(str, conf.quotas.all.keys()))
                )
            quotas[name] = Integer()(value)
        return quotas


class CustomerPasswordResetTokenValidator(object):
    def __call__(self, value):
        try:
            return CustomerPasswordResetToken.get(value)
        except errors.PasswordResetTokenInvalid as e:
            raise ValidateError(e.message)


class ConfirmEmailTokenValidator(object):
    def __call__(self, value):
        return EmailConfirmationToken.get(value)


class CustomerTypeValidator(PredefinedChoose):
    FIELDS = (Customer.CUSTOMER_TYPE_PRIVATE_PERSON, Customer.CUSTOMER_TYPE_LEGAL_ENTITY)


class CustomerOpenStackDashboardValidator(PredefinedChoose):
    FIELDS = Customer.ALL_PANELS


CustomerInfoValidator = JSON.construct_validator({
    "name": (StringWithLimits(max_length=64), None),
    "birthday": (Day(), None),
    "country": (StringWithLimits(max_length=32), None),
    "city": (StringWithLimits(max_length=32), None),
    "address": (StringWithLimits(max_length=254), None),
    "passport_series_number": (StringWithLimits(max_length=16), None),
    "passport_issued_by": (StringWithLimits(max_length=254), None),
    "passport_issued_date": (Day(), None),
    "telephone": (StringWithLimits(max_length=16), None),

    "contract_number": (StringWithLimits(max_length=64), None),
    "contract_date": (Day(), None),
    "organization_type": (StringWithLimits(max_length=8), None),
    "full_organization_name": (StringWithLimits(max_length=254), None),
    "primary_state_registration_number": (StringWithLimits(max_length=16), None),
    "individual_tax_number": (StringWithLimits(max_length=16), None),
    "legal_address_country": (StringWithLimits(max_length=32), None),
    "legal_address_city": (StringWithLimits(max_length=32), None),
    "legal_address_address": (StringWithLimits(max_length=254), None),
    "location_country": (StringWithLimits(max_length=32), None),
    "location_city": (StringWithLimits(max_length=32), None),
    "location_address": (StringWithLimits(max_length=254), None),
    "general_manager_name": (StringWithLimits(max_length=254), None),
    "general_accountant_name": (StringWithLimits(max_length=254), None),
    "contact_person_name": (StringWithLimits(max_length=254), None),
    "contact_person_position": (StringWithLimits(max_length=64), None),
    "contact_telephone": (StringWithLimits(max_length=16), None),
    "contact_email": (Email(), None)
})

CustomerIdExpand = ModelId(Customer, errors.CustomerNotFound)
CustomerId = ModelId(Customer, errors.CustomerNotFound, expand=False)


class DateHour(DateTime):

    UNDIVIDED_TPL = "%Y%m%d%H"
    UNDIVIDED_LEN = len("2013012800")

    DIVIDED_TPL = "%Y-%m-%dT%H"
    DIVIDED_LEN = len("2013-01-28T00")

    def unix(self, timestamp):
        timestamp = super().unix(timestamp)
        if timestamp.minute != 0 or timestamp.second != 0 or timestamp.microsecond != 0:
            raise ValueError()

        return timestamp

    def __call__(self, value):
        result = super().__call__(value)
        if not result:
            raise ValidateError(_("Incorrect date format. The expected format is %s or %s" %
                                  (self.UNDIVIDED_TPL, self.DIVIDED_TPL)))

        return result.replace(tzinfo=Date.UTC_TZ)


class DateHourBeforeNow(DateHour):
    def __init__(self, gap=None):
        if not isinstance(gap, timedelta):
            gap = timedelta(seconds=gap or 0)
        self.gap = gap

    def __call__(self, value):
        result = super().__call__(value)
        if result - self.gap > utcnow():
            raise ValidateError(_("Date from future"))
        return result


class CustomerApi(CabinetApi):
    CABINET_FRONTEND_PATH = "/lk/"

    @staticmethod
    def validate_g_recaptcha_response(g_recaptcha_response, bot_secret):
        import requests
        from requests.exceptions import RequestException

        if not conf.api.secure.recaptcha.validate:
            return True

        if bot_secret:
            return True
        if not g_recaptcha_response:
            logbook.warning("g_recaptcha_response is empty")
            return False

        url = conf.api.secure.recaptcha.url
        data = {"secret": conf.api.secure.recaptcha.secret,
                "response": g_recaptcha_response}
        try:
            siteverify = requests.post(url, data=data, timeout=conf.api.secure.recaptcha.timeout)
        except requests.exceptions.RequestException as e:
            logbook.warning("Recaptcha verify failed {} {}: {}", url, data, e)
            return False

        if siteverify.status_code != 200:
            logbook.warning("Recaptcha response incorrect {} {}: {}", url, data, siteverify.status_code)
            return False

        try:
            response = siteverify.json()
        except ValueError:
            logbook.warning("Recaptcha response incorrect {} {}: {}", url, data, siteverify.content)
            return False

        success = response.get("success")
        if not success:
            logbook.warning("Recaptcha response is not success {} {}: {}", url, data, response)
            return False

        return True

    @post("customer/", api_type=API_ALL)
    @enable_cors
    @check_params(
        email=(Email, IndexSizeLimit),
        password=PasswordValidator,
        detailed_info=CustomerInfoValidator,
        make_prod=Bool,
        customer_type=CustomerTypeValidator,
        bot_secret=SecretSign("bot_secret"),
        g_recaptcha_response=String,
        withdraw_period=WithdrawPeriod,
        promo_code=String,
        locale=ActiveLocale()
    )
    @autocommit
    def new_customer(self, email, password=None, detailed_info=None, make_prod=False, customer_type=None,
                     bot_secret=None, g_recaptcha_response=None, withdraw_period=None, promo_code=None, locale=None):
        """
        Registration of new customer.

        :param Email email: Customer email
        :param str password: Customer password
        :param dict detailed_info: Dictionary with detailed customer's info.
        :param bool make_prod: Creates production customer. Available only from admin api
        :param str customer_type: customer type: legal entity or private person(default). Available only from admin api
        :param withdraw_period: Customer withdraw period. Available only from admin api
        :param str promo_code: Promo code value for registration.
        :param str locale: Customer locale, it is used for report generating
        :param str bot_secret:  Self signed string which allows to create new customer without recaptcha
        :param str g_recaptcha_response: Response from recaptcha service
        :return dict customer_info: Customer info.

        **Example**::

            {
                "customer_info": {
                    {"customer_id": 1,
                     "deleted": null,
                     "email": "customer@test.ru",
                     "detailed_info": {
                        "name": "John Doe",
                        "birthday": "1990-10-17",
                        "country": "Russia",
                        "city": "Moscow",
                        "address": "Example street, 62",
                        "telephone": "8 (909) 515-77-07"
                     },
                     "created": "2015-04-24T11:14:22",
                     "blocked": false,
                     "customer_mode": "test",
                     "customer_type": "private",
                     "withdraw_period": "month",
                     "withdraw_date": "2015-07-01",
                     "balance_limit": 0,
                     "account": {
                         "rub": {"balance": "1035.22", "current": "1035.22", "withdraw": "0.00"}
                     },
                     "os_tenant_id": 1,
                     "os_user_id": 1,
                     "os_dashboard": "horizon",
                     "promo_code": [{"value": "code_value_1"}, {"value": "code_value_2"}]
                     }
                }
            }

        """
        if request_api_type() == API_CABINET:
            if conf.promocodes.promo_registration_only:
                if promo_code is None:
                    raise errors.PromocodeOnly()
                if not self.check_promocode(promo_code):
                    raise errors.PromocodeInvalid()
            else:
                promo_code = None
        else:
            promo_code = None

        if request_api_type() == API_CABINET and \
                not self.validate_g_recaptcha_response(g_recaptcha_response, bot_secret):
            raise errors.BotVerifyFailed()

        if request_api_type() == API_CABINET:
            make_prod = False
            customer_type = Customer.CUSTOMER_TYPE_PRIVATE_PERSON
            withdraw_period = None

        if make_prod and not self.validate_customer_production_info(detailed_info or {}, customer_type):
            raise errors.ProductionModeNeedMoreInfo()

        customer = Customer.new_customer(email, password, None, detailed_info=detailed_info,
                                         withdraw_period=withdraw_period, make_prod=make_prod,
                                         customer_type=customer_type, promo_code=promo_code, locale=locale)
        self.send_confirmation_email(customer, None)

        if request_api_type() == API_CABINET:
            token = CustomerToken.create(customer)
            setattr(local_properties, 'user_token', token)
            cookie_flags = {"httponly": True}
            if conf.api.secure_cookie and not conf.test:
                cookie_flags["secure"] = True

            bottle.response.set_cookie(CABINET_TOKEN_NAME, token.id, path='/', **cookie_flags)

        return {"customer_info": display(customer)}

    @staticmethod
    def check_promocode(promo_code):
        code_exp_date = conf.promocodes.codes.get(promo_code, None)
        if code_exp_date is None:
            return False
        date_today = utcnow().date()
        if code_exp_date > date_today:
            return True
        return False

    @options("customer/", api_type=API_ALL)
    @enable_cors
    def new_customer_option(self):
        r = bottle.HTTPResponse("")
        r.content_type = "text/html"
        return r

    @staticmethod
    def send_confirmation_email(customer, user_id):
        if customer.deleted:
            raise errors.CustomerRemoved()

        base_url = request_base_url()

        token = EmailConfirmationToken.create(customer)
        url = urljoin(base_url, posixpath.join(CustomerApi.CABINET_FRONTEND_PATH, "confirmation", token.id))
        subject, body = MessageTemplate.get_rendered_message(MessageTemplate.CUSTOMER_CONFIRMATION,
                                                             language=preferred_language(),
                                                             customer_name=customer.get_name(), confirm_url=url)

        logbook.info("Sending confirmation email to {}. Token {}", customer.email, token)
        CustomerHistory.send_confirm_email(customer, user_id, "Sending confirmation email")
        db.session.commit()
        send_email.delay(customer.email, subject, body)

    @post("auth/")
    @enable_cors
    @check_params(
        email=(Email, IndexSizeLimit),
        password=PasswordValidator,
        return_customer_info=Bool
    )
    def login(self, email, password, return_customer_info=False):
        """
        Auth customer by email and password. This method setup cookie which can be used in next requests.

        :param Email email: Customer email
        :param password: Customer password
        :param return_customer_info: Return info of logged in customer
        :return dict customer_info: Customer info.

        **Example**::

            {
                "customer_info": {
                    {"customer_id": 1,
                     "deleted": null,
                     "email": "customer@test.ru",
                     "detailed_info": {
                        "name": "John Doe",
                        "birthday": "1990-10-17",
                        "country": "Russia",
                        "city": "Moscow",
                        "address": "Example street, 62",
                        "telephone": "8 (909) 515-77-07"
                     },
                     "tariff_id": 1,
                     "created": "2015-04-24T11:14:22",
                     "blocked": false,
                     "customer_mode": "test",
                     "customer_type": "private",
                     "withdraw_period": "month",
                     "withdraw_date": "2015-07-01",
                     "balance_limit": 0,
                     "account": {
                         "rub": {"balance": "1035.22", "current": "1035.22", "withdraw": "0.00"}
                     },
                     "os_tenant_id": 1,
                     "os_user_id": 1,
                     "promo_code": [{"value": "code_value_1"}, {"value": "code_value_2"}]
                     }
                }
            }
        """
        token, customer = Customer.login(email, password)
        # need to change request_log.py for extracting customer info
        setattr(local_properties, 'user_token', token)
        cookie_flags = {"httponly": True}
        if conf.api.secure_cookie and not conf.test:
            cookie_flags["secure"] = True

        bottle.response.set_cookie(CABINET_TOKEN_NAME, token.id, path='/', **cookie_flags)
        customer_info = display(customer) if return_customer_info else {}
        return {"customer_info": customer_info}

    @options("auth/", api_type=API_ALL)
    @enable_cors
    def login_option(self):
        r = bottle.HTTPResponse("")
        r.content_type = "text/html"
        return r

    @post("logout/")
    @check_params(token=CustomerTokenId)
    def logout(self, token):
        """
        Stop customer session.
        """
        CustomerToken.remove(token)
        bottle.response.delete_cookie(CABINET_TOKEN_NAME, path="/")
        return {}

    # noinspection PyUnusedLocal
    @put('customer/me/')
    @check_params(
        all_parameters=True,
        token=CustomerTokenId,
        password=PasswordValidator,
        customer_type=CustomerTypeValidator,
        detailed_info=CustomerInfoValidator,
        locale=ActiveLocale()
    )
    @autocommit
    def update_by_customer(self, token, all_parameters, password=None, detailed_info=None, locale=None,
                           customer_type=None):
        """
        Update customer self profile.

        :param str password: New customer password [optional]
        :param str customer_type: New customer type [optional]
        :param dict detailed_info: Dictionary with detailed customer's info [optional].

        :return dict customer_info: Customer info
        """
        all_parameters.pop("detailed_info", None)

        if not all_parameters and not detailed_info:
            raise errors.NothingForUpdate()

        customer = Customer.get_by_id(token.customer_id)
        if all_parameters:
            customer.update(all_parameters)

        if detailed_info:
            if customer.customer_mode != Customer.CUSTOMER_TEST_MODE:
                raise errors.NothingForUpdate("You could edit your contact information only in test mode. "
                                              "Please, contact to your account manager")
            customer.update(new_info_params=detailed_info)
        return {"customer_info": customer.display()}

    # noinspection PyUnusedLocal
    @put('customer/<customer>/', api_type=API_ADMIN)
    @check_params(
        all_parameters=True,
        token=TokenManager,
        customer=CustomerIdExpand,
        password=PasswordValidator,
        email=(Email, IndexSizeLimit),
        detailed_info=CustomerInfoValidator,
        tariff=TariffIdExpand,
        comment=String(),
        withdraw_period=WithdrawPeriod,
        balance_limit=DecimalMoney,
        customer_type=CustomerTypeValidator,
        locale=ActiveLocale(),
        os_dashboard=CustomerOpenStackDashboardValidator,
        confirm_email=Bool
    )
    @autocommit
    def update_other(self, token, customer, all_parameters, password=None, email=None,
                     detailed_info=None, tariff=None, comment=None, withdraw_period=None, balance_limit=None,
                     customer_type=None, locale=None, os_dashboard=None, confirm_email=None):
        """
        Update customer profile from admin panel.

        :param Customer customer: Customer id
        :param str password: New password [optional]
        :param str email: New email [optional]
        :param dict detailed_info: Dictionary with detailed customer's info [optional].
        :param Id tariff: New tariff id
        :param str comment: Description why this changes were done
        :param str withdraw_period: New withdraw period
        :param int balance_limit: New balance limit
        :param str customer_type: New customer_type value, can be one from set ("private", "entity") [optional]
        :param locale: Customer locale, it is used for report generating
        :param os_dashboard: OpenStack dashboard selector. Available values: ['horizon', 'skyline', 'both']
        :param confirm_email: mark customer email as confirmed if it is true

        :return dict detailed_info: Customer info. Please see example in  :obj:`PUT /0/customer/me/`
        """
        all_parameters.pop("customer", None)
        all_parameters.pop("detailed_info", None)
        all_parameters.pop("comment", None)
        all_parameters.pop("confirm_email", None)

        if not all_parameters and not detailed_info and not confirm_email:
            raise errors.NothingForUpdate()

        if tariff:
            customer.update_tariff(tariff.tariff_id, token.user_id, comment)
            all_parameters.pop("tariff")

        customer.update(all_parameters, detailed_info, token.user_id, comment)

        if confirm_email and not customer.email_confirmed:
            customer.confirm_email()
        return {"customer_info": customer.display()}

    @put('customer/group/', api_type=API_ADMIN)
    @check_params(
        all_parameters=True,
        customers=List(CustomerIdExpand),
        token=TokenAccount,
        comment=String(),
        tariff=TariffIdExpand,
        deferred_date=DeferredDate(),
        withdraw_period=WithdrawPeriod,
        balance_limit=DecimalMoney,
        customer_type=CustomerTypeValidator,
        locale=ActiveLocale()
    )
    @autocommit
    def group_update(self, token, customers, all_parameters, tariff=None, deferred_date=None, comment=None,
                     withdraw_period=None, balance_limit=None, customer_type=None, locale=None):
        """
        Group update of customer profiles from admin panel. (allowed for admin and account director)

        :param List[Customer] customers: Customer ids
        :param Id tariff: New tariff id
        :param Date deferred_date: Time when new tariff should applicable/
        :param str withdraw_period: New withdraw period
        :param str comment: Description why this changes were done
        :param int balance_limit: New balance limit
        :param str customer_type: New customer_type value, can be one from set ("private", "entity") [optional]
        :param locale: Customer locale, it is used for report generating

        :return list detailed_info: List of customer info. Please see example in  :obj:`PUT /0/customer/me/`
        """

        if not customers:
            raise errors.CustomerNotFound()

        all_parameters.pop("tariff", None)
        all_parameters.pop("comment", None)
        all_parameters.pop("customers", None)
        all_parameters.pop("deferred_date", None)

        if not all_parameters and not tariff:
            raise errors.NothingForUpdate()

        customer_info = []
        for customer in customers:
            if tariff:
                if deferred_date:
                    if tariff.mutable:
                        raise errors.AssignMutableTariff()
                    Deferred.create(customer.customer_id, tariff.tariff_id, token.user_id, deferred_date, comment)
                else:
                    customer.update_tariff(tariff.tariff_id, token.user_id, comment)
            if all_parameters:
                customer.update(all_parameters, user_id=token.user_id, comment=comment)
            customer_info.append(customer.display())
        return {"customer_info": customer_info}

    @get("customer/me/")
    @check_params(token=CustomerTokenId)
    def get_info(self, token):
        """
        Return customer info of current customer

        :return dict customer_info: Customer info.

                **Example**::

                    {
                        "customer_info": {
                            {"name": "John Doe",
                             "blocked": false,
                             "email": "customer@test.ru",
                             "birthday": "1990-10-17",
                             "country": "Russia",
                             "city": "Moscow",
                             "address": "Example street, 62",
                             "telephone": "8 (909) 515-77-07",
                             "created": "2015-04-24T11:14:22",
                             "withdraw_period": "month",
                             "withdraw_date": "2015-07-01"
                             "balance_limit": 0,
                             "account": {
                                 "rub": {"balance": "1035.22", "current": "1035.22", "withdraw": "0.00"}
                             },
                             "tariff_id": 1,
                             "currency": "rub",
                             "os_tenant_id": 1,
                             "os_user_id": 1,
                             "promo_code": [{"value": "code_value_1"}, {"value": "code_value_2"}]
                             }
                            }
                        }
                    }

        **Note**: Each customer can have several accounts. Account is created for each used currency. Account
        contains two 'subaccount'. Balance is like classic bank account. You can put money to it and money can be
        charged from it. 'Withdraw' means how many resources were used in current payment period (month by default)
        In the end of payment period 'withdraw' is charged from 'balance'.
        'Current' is 'Balance' - 'Withdraw'

        """
        customer = Customer.get_by_id(token.customer_id)
        if customer is None:
            logbook.debug("Customer not found by id {}", token.customer_id)
            raise errors.CustomerInvalidToken()

        return {"customer_info": display(customer)}

    @delete("customer/<customer>/", api_type=API_ADMIN)
    @check_params(token=TokenManager, customer=CustomerIdExpand, comment=String())
    @autocommit
    def remove(self, token, customer, comment=None):
        """
        Remove customer

        :param Id customer: Customer Id
        :param str comment: Description why customer is goint to be removed
        :return: None
        """

        customer.remove(token.user_id, comment)
        CustomerToken.remove(token)
        return {}

    @get("customer/<customer>/", api_type=API_ADMIN)
    @check_params(
        token=TokenId,
        customer=CustomerIdExpand)
    def get_info_by_manager(self, customer):
        """
        Return customer info of current customer

        :return dict customer_info: Customer info.

                **Example**::

                    {
                        "customer_info": {
                            "email": "customer@test.ru",
                            "name": "John Doe",
                            "deleted": null,
                            "detailed_info": {
                                "birthday": "1990-10-17",
                                "country": "Russia",
                                "city": "Moscow",
                                "address": "Example street, 62",
                                "telephone": "8 (909) 515-77-07"
                            },
                            "created": "2015-04-24T11:14:22",
                            "withdraw_period": "month",
                            "withdraw_date": "2015-07-01",
                            "balance_limit": 0,
                            "account": {"rub": {"balance": "1035.22", "current": "1035.22", "withdraw": "0.00"}},
                            "os_tenant_id": 1,
                            "os_user_id": 1,
                            "promo_code": [{"value": "code_value_1"}, {"value": "code_value_2"}]
                        }
                    }
        """
        return {"customer_info": display(customer)}

    # noinspection PyUnusedLocal
    @get("customer/", api_type=API_ADMIN)
    @check_params(
        token=TokenId,
        email=Email,
        name=StringWithLimits(max_length=256),
        birthday=Day(),
        country=StringWithLimits(max_length=32),
        city=StringWithLimits(max_length=32),
        address=StringWithLimits(max_length=254),
        telephone=StringWithLimits(max_length=16),
        page=IntRange(1),
        limit=IntRange(1, conf.api.pagination.limit),
        all_parameters=True,
        tariff_ids=List(TariffId),
        created_before=Date(),
        created_after=Date(),
        visibility=Visibility(),
        blocked=Bool(),
        customer_mode=Choose(Customer.ALL_MODES),
        customer_type=Choose(Customer.ALL_TYPES),
        sort=List(SortFields(Customer))
    )
    def list(self, token, email=None, name=None, birthday=None, country=None,
             city=None, address=None, telephone=None, all_parameters=None,
             blocked=None, customer_mode=None, customer_type=None,
             tariff_ids=None, created_before=None, created_after=None,
             page=1, limit=conf.api.pagination.limit, sort=('email',),
             visibility=Visibility.DEFAULT):
        """
        Return filtered customer list.

        :param Email email: Customer email
        :param name: Customer full name
        :param birthday: Customer date of birth
        :param country: Customer country
        :param city: Customer city
        :param address: Customer address
        :param telephone: Customer telephone
        :param tariff_ids: IDs' list of customer's tariff
        :param date created_before: filters customers with creation date before this date
        :param date created_after: filters customers with creation date after this date
        :param page: page number
        :param limit: number of customers per page
        :return List customer_list: List of customers for this query.
        :param str visibility: Visibility options
                               *visible* - Only active customers, [by default]
                               *deleted* - Only removed customers.
                               *all* - All customers.
        :param bool blocked: Customer blocked or not
        :param str customer_type: Customer type options
                                    *private* - private person
                                    *entity* - legal entity
        :param str customer_mode: Customer mode options
                                    *test* - Customer in test period
                                    *production* - Production mode
                                    *pending_prod* - Customer going to production mode

        **Example**::

            {
                "customer_list": {
                    "per_page": 100,
                    "total": 2,
                    "page": 0
                    "items": [
                    {
                        "account": {
                            "USD": {
                                "balance": "10.00",
                                "withdraw": "0.00",
                                "current": "10.00"
                            }
                        },
                        "detailed_info": {
                            "name": "John Doe",
                            "birthday": "1999-09-09",
                            "country": "Russia",
                            "city": "Moscow",
                            "address": "Example street, 62",
                            "telephone": "89876543212"
                        },
                        "created": "2013-09-19T06:42:03.747000+00:00",
                        "deleted": null,
                        "customer_id": "1",
                        "email": "list_test0@test.ru",
                        "withdraw_period": "month",
                        "withdraw_date": "2015-07-01"
                        "email_confirmed": false,
                        "customer_mode": "test",
                        "customer_type": "private",
                        "tariff_id": 1,
                        "blocked": false,
                        "currency": "USD",
                        "balance_limit": 0,
                        "os_tenant_id": null,
                        "os_user_id": null,
                        "promo_code": []
                    },
                    {
                        "detailed_info": {
                            "name": Petr Company, LTD,
                            "contract_number": "123456",
                            "contract_date": "1970-01-01"
                            "contact_person_name": "John Doe",
                            "general_manager_name": "Petr Petrovich Petrov",
                            "location_country": "Russia",
                            "location_city": "Petrozavodsk",
                            "location_address": "Example street, 63",
                            "contact_telephone": "89123456789"
                        },
                        "created": "2013-09-19T06:42:03.747000+00:00",
                        "deleted": null,
                        "customer_id": "2",
                        "email": "list_test1@test.ru",
                        "withdraw_period": "month",
                        "withdraw_date": "2015-07-01",
                        "email_confirmed": true,
                        "customer_mode": "production",
                        "customer_type": "entity",
                        "tariff_id": 2,
                        "blocked": false,
                        "currency": "USD",
                        "balance_limit": 0,
                        "os_tenant_id": 1,
                        "os_user_id": 1,
                        "promo_code": [{"value": "code_value_1"}, {"value": "code_value_2"}]
                    }]}
            }
        """
        # noinspection PyUnresolvedReferences
        all_parameters.setdefault("limit", limit)
        # noinspection PyUnresolvedReferences
        all_parameters.setdefault("page", page)
        # noinspection PyUnresolvedReferences
        all_parameters.setdefault("sort", sort)

        all_parameters.pop("visibility", None)
        query = Customer.filter(all_parameters, visibility=visibility)
        return {"customer_list": self.paginated_list(query)}

    @post("customer/confirm_email/<confirm_token>/")
    @check_params(confirm_token=ConfirmEmailTokenValidator)
    @autocommit
    def email_confirm(self, confirm_token):
        """
        Confirm customer email

        :param String confirm_token:  Token which was returned by method
                :obj:`PUT /0/customer/confirm_email/ <view.PUT /0/customer//confirm_email/>`;

        :return password_token: If customer password is not set this field contains password_reset token
        """
        # noinspection PyUnresolvedReferences
        customer = Customer.get_by_id(confirm_token.customer_id)
        if not customer:
            raise errors.CustomerInvalidToken()
        customer.confirm_email()
        EmailConfirmationToken.remove(confirm_token)
        password_token = None
        if not customer.password:
            # customer password is not set, because customer was created by admin
            token = CustomerPasswordResetToken.create(customer)
            password_token = token.id

        return {"password_token": password_token}

    @put("customer/me/confirm_email/")
    @check_params(
        token=CustomerTokenId)
    def send_email_confirm_self(self, token):
        """
        Send confirmation email to yourself.

        :return: None
        """
        customer = Customer.get_by_id(token.customer_id)
        if not customer:
            raise errors.CustomerInvalidToken()
        self.send_confirmation_email(customer, None)
        return {}

    @put("customer/<customer>/confirm_email/", api_type=API_ADMIN)
    @check_params(
        token=TokenId,
        customer=CustomerIdExpand)
    def send_email_confirm(self, token, customer):
        """
        Send confirmation email to customer.

        :return: None
        """
        self.send_confirmation_email(customer, token.user_id)
        return {}

    @get("customer/<customer>/tariff/", api_type=API_ADMIN)
    @check_params(
        token=TokenId,
        customer=CustomerIdExpand)
    def get_customer_tariff(self, customer):
        """
        Return tariff description for the customer

        :param Id customer: Customer Id

        :return Dict tariff_info: Dict with tariff info
        """
        return {"tariff_info": display(customer.tariff)}

    @get("customer/me/tariff/")
    @check_params(token=CustomerTokenId)
    def get_self_tariff(self, token):
        """
        Return tariff description for the customer

        :return Dict tariff_info: Dict with tariff info
        """
        customer = Customer.get_by_id(token.customer_id)
        if customer is None:
            logbook.debug("Customer not found by id {}", token.customer_id)
            raise errors.CustomerInvalidToken()

        return {"tariff_info": customer.tariff.display_for_customer()}

    @get("customer/me/subscribe/")
    @check_params(token=CustomerTokenId)
    def subscription_info(self, token):
        """

        Returns info about customer's subscriptions to customer

        :return Dict subscribe: dict with info

        **Example**::

            {"subscribe":
                {
                    "news": {"enable": False, "email": ["a@a.ru", "b@b.ru"]},
                    "billing":  {"enable": False, "email": ["a@a.ru", "b@b.ru"]},
                    "status": {"enable": True, "email": ["c@c.ru"]}
                }
            }
        """
        customer = Customer.get_by_id(token.customer_id)
        if not customer:
            raise errors.CustomerNotFound()
        return {'subscribe': customer.subscription_info()}

    @put("customer/me/subscribe/")
    @check_params(
        token=CustomerTokenId,
        subscribe=Subscribe)
    @autocommit
    def update_subscription(self, token, subscribe):
        """

        Self update customer's subscriptions.
        Parameters must be sent as json object.

        :param dict subscribe: Info about customer's subscriptions to update

        **Example**::

            {"subscribe":
                {
                    "news": {"enable": False, "email": ["a@a.ru", "b@b.ru"]},
                    "billing":  {"enable": False, "email": ["a@a.ru", "b@b.ru"]},
                    "status": {"enable": True, "email": ["c@c.ru"]}
                }
            }

        :return dict subscribe: The same as subscribe argument
        """
        customer = Customer.get_by_id(token.customer_id)
        if not customer:
            raise errors.CustomerNotFound()
        customer.subscriptions_update(subscribe, None)
        return {'subscribe': customer.subscription_info()}

    @get("customer/<customer>/subscribe/", api_type=API_ADMIN)
    @check_params(
        token=TokenId,
        customer=CustomerIdExpand)
    def subscription_info_by_user(self, customer):
        """

        Returns info about customer's subscriptions to user

        :param Id customer: Customer Id

        :return Dict subscribe: dict with info

        **Example**::

            {"subscribe":
                {
                    "news": {"enable": False, "email": ["a@a.ru", "b@b.ru"]},
                    "billing":  {"enable": False, "email": ["a@a.ru", "b@b.ru"]},
                    "status": {"enable": True, "email": ["c@c.ru"]}
                }
            }
        """
        return {'subscribe': customer.subscription_info()}

    @put("customer/<customer>/subscribe/", api_type=API_ADMIN)
    @check_params(
        token=TokenId,
        customer=CustomerIdExpand,
        subscribe=Subscribe)
    @autocommit
    def update_subscription_by_user(self, token, customer, subscribe):
        """

        Update customer's subscriptions by user.
        Parameters must be sent as json object.

        :param Id customer: Customer Id
        :param dict subscribe: Info about customer's subscriptions to update

            **Example**::

                {"subscribe":
                    {
                        "news": {"enable": False, "email": ["a@a.ru", "b@b.ru"]},
                        "billing":  {"enable": False, "email": ["a@a.ru", "b@b.ru"]},
                        "status": {"enable": True, "email": ["c@c.ru"]}
                    }
                }

        :return dict subscribe: The same as subscribe argument

        """
        customer.subscriptions_update(subscribe, token.user_id)
        return {'subscribe': customer.subscription_info()}

    @get("customer/<customer>/deferred/", api_type=API_ADMIN)
    @check_params(
        token=TokenId,
        customer=CustomerIdExpand)
    def get_deferred(self, customer):
        """
        Returns deferred changes for customer.

        :param Id customer: Customer Id
        :return Dict deferred: Info about deferred changes

        **Example**::

            {
               {"deferred":
                  {
                    "user": {"user_id": 1, "name": "Super Admin"},
                    "date": "2015-06-01T12:59:40+00:00",
                    "comment": null,
                    "tariff": {"description": "", "mutable": true,
                               "deleted": null, "parent_id": null, "default": null,
                               "tariff_id": 2,
                               "localized_name": {"ru": "xxxx", "en": "some name"},
                               "created": "2015-06-01T12:59:38+00:00"}}}
            }
        """
        deferred = customer.get_deferred()
        if deferred:
            deferred = deferred.display()
        return {"deferred": deferred}

    @put("customer/<customer>/deferred/", api_type=API_ADMIN)
    @check_params(
        token=TokenManager,
        customer=CustomerId,
        tariff=TariffIdExpand,
        date=DeferredDate(),
        comment=String())
    @autocommit
    def set_deferred(self, token, customer, tariff, date, comment=None):
        """
        Update deferred changes for customer.

        :param Id customer: Customer Id
        :param Id tariff: New tariff ID
        :param Date date: Date when tariff should be apply
        :param Str comment: Comment why the tariff was changed

        :return Dict deferred: Info about deferred changes

        **Example**::

            {
               {"deferred":
                  {
                    "user": {"user_id": 1, "name": "Super Admin"},
                    "date": "2015-06-01T12:59:40+00:00",
                    "comment": null,
                    "tariff": {"description": "", "mutable": true,
                               "deleted": null, "parent_id": null, "default": null,
                               "tariff_id": 2,
                               "localized_name": {"ru": "xxxx", "en": "some name"},
                               "created": "2015-06-01T12:59:38+00:00"}}}
            }
        """
        if tariff.mutable:
            raise errors.AssignMutableTariff()
        Deferred.create(customer, tariff.tariff_id, token.user_id, date, comment)
        deferred = Deferred.get_by_customer(customer)
        return {"deferred": deferred.display()}

    @delete("customer/<customer>/deferred/", api_type=API_ADMIN)
    @check_params(
        token=TokenManager,
        customer=CustomerIdExpand)
    @autocommit
    def cancel_deferred(self, customer):
        """
        Cancel deferred changes for customer.

        :param Id customer: Customer Id
        :return: None
        """

        Deferred.delete_by_customer(customer.customer_id)
        return {}

    @post("customer/<customer>/deferred/force/", api_type=API_ADMIN, internal=True)
    @check_params(
        token=TokenManager,
        customer=CustomerIdExpand)
    @autocommit
    def force_deferred(self, customer):
        """
        Force to apply deferred changes for the customer. This method can be used only in tests!

        :param Id customer: Customer Id

        :return: None
        """
        deferred = Deferred.get_by_customer(customer.customer_id)
        if deferred:
            Deferred.do_deferred_changes(deferred)
        else:
            error = errors.NotFound()
            error.message = "Deferred changes are not found"
            raise error
        return {}

    @post("customer/support/")
    @check_params(
        token=CustomerTokenId,
        subject=String,
        body=String,
        copy=EmailList(', ')
    )
    def send_question(self, token, subject, body, copy=None):
        """
        Sends customer's question to support

        :param str subject: subject of message
        :param str body: message text
        :param list copy: list of CC emails
        :return: None
        """

        customer = Customer.get_by_id(token.customer_id)
        if copy is None:
            copy = [customer.email]
        else:
            copy.append(customer.email)
        send_email.delay(conf.customer.support.email, subject, body, cc=copy)
        return {}

    @put("customer/<customer>/balance/", api_type=API_ADMIN)
    @check_params(
        token=TokenManager,
        customer=CustomerIdExpand,
        comment=String(),
        currency=ActiveCurrencies,
        amount=DecimalMoney
    )
    @autocommit
    def update_balance(self, token, customer, amount, comment, currency=None):
        """
        Manual balance change.

        :param ID customer: Customer ID.
        :param currency: Currency Id. Only active currencies are possible. By default current tariff currency is used
        :param str amount: Money amount. The following format is allowed: "xxx.xx". If the amount
                             is positive, balance will be increased. Otherwise, the balance will be decreased
        :param str comment: Comment for the balance changing

        :return Dict customer_info: Customer info

        """
        customer.modify_balance(amount, currency, token.user_id, comment)
        db.session.commit()
        return {"customer_info": display(Customer.get_by_id(customer.customer_id))}

    @get("customer/<customer>/balance/history/", api_type=API_ADMIN)
    @check_params(
        token=TokenId,
        before=Date(),
        after=Date(),
        customer=CustomerIdExpand,
        limit=IntRange(10, 1000)
    )
    def account_history(self, customer, after=None, before=None, limit=1000):
        """
        Return list of account changes.

        :param ID customer: Customer ID.
        :param Date before: Returns events which were happened before this date
        :param Date after: Returns events which were happened after this date
        :param int limit: Number of changes in the return list

        :return list account_history: List of changes

        """
        history = customer.get_account_history(after, before, limit)
        return {"account_history": display(history)}

    @get("customer/me/balance/history/")
    @check_params(
        token=CustomerTokenId,
        before=Date(),
        after=Date(),
        limit=IntRange(10, 1000)
    )
    def account_history_self(self, token, after=None, before=None, limit=1000):
        """
        Return list of account changes.

        :param Date before: Returns events which were happened before this date
        :param Date after: Returns events which were happened after this date
        :param int limit: Number of changes in the return list

        :return list account_history: List of changes

        """
        customer = Customer.get_by_id(token.customer_id)
        if not customer:
            raise errors.CustomerInvalidToken()
        history = customer.get_account_history(after, before, limit)
        return {"account_history": display(history, short=True)}

    @put("customer/<customer>/block/", api_type=API_ADMIN)
    @check_params(
        token=TokenManager,
        blocked=Bool,
        customer=CustomerIdExpand,
        message=String
    )
    @autocommit
    def block(self, token, customer, blocked=True, message=None):
        """
        Block or unblock specific customer

        :param ID customer: Customer ID.
        :param bool blocked: Customer became block if it is true and unblock otherwise
        :param str message: Admin's message
        :return Dict customer_info: Customer info

        """
        customer.block(blocked, token.user_id, message)
        return {"customer_info": display(customer)}

    @put("customer/<customer>/quota/", api_type=API_ADMIN)
    @check_params(
        token=TokenManager,
        customer=CustomerIdExpand,
        limits=QuotaValidator
    )
    @autocommit
    def change_quota(self, token, customer, limits):
        """
        This method allows changing customer's resources limits by user with role >=Manager

        :param dict limits: Dictionary with info about limits to update

        **Example**::

            {
                "maxImageMeta": 128,
                "maxTotalInstances": 1,
                ...
            }

        :return dict quota: Dict with info about quota

        **Example**::

            {"quota":
                [{"limit_id": maxImageMeta,
                  "localization_description":
                    {"en": "The maximum number of key-value pairs per image for the project.",
                     "ru": "Максимальное количество пар ключ-значение в метаданных образа, всего на тенант."},
                  "value": 128},
                 {...}]

            }

        """
        customer.quota_update(limits, token.user_id)
        return {"quota": customer.quota_info()}

    @post("customer/<customer>/quota/", api_type=API_ADMIN)
    @check_params(
        token=TokenManager,
        customer=CustomerIdExpand,
        template=TEMPLATE_VALIDATOR
    )
    @autocommit
    def change_template(self, token, customer, template):
        """
        Applies quota template to customer

        :param template: Template name in config
        :return list quota: Dict with info about quota

        **Example**::

            {"quota":
                [{"limit_id": maxImageMeta,
                  "localization_description":
                    {"en": "The maximum number of key-value pairs per image for the project.",
                     "ru": "Максимальное количество пар ключ-значение в метаданных образа, всего на тенант."},
                  "value": 128},
                 {...}]

            }
        """
        customer.quota_update(conf.template[template], token.user_id)
        return {"quota": customer.quota_info()}

    @get("customer/<customer>/quota/", api_type=API_ADMIN)
    @check_params(
        token=TokenId,
        customer=CustomerIdExpand
    )
    def quota_info(self, customer):
        """
        Returns customer's limits.

        :return list quota: Dict with info about quota

        **Example**::

            {"quota":
                [{"limit_id": maxImageMeta,
                  "localization_description":
                    {"en": "The maximum number of key-value pairs per image for the project.",
                     "ru": "Максимальное количество пар ключ-значение в метаданных образа, всего на тенант."},
                  "value": 128},
                 {...}]

            }
        """
        return {"quota": customer.quota_info()}

    @get("customer/me/quota/")
    @check_params(
        token=CustomerTokenId
    )
    def quota_info_self(self, token):
        """
        Returns limits of current customer

        :return list quota: Dict with info about quota

        **Example**::

            {"quota":
                [{"limit_id": maxImageMeta,
                  "localization_description":
                    {"en": "The maximum number of key-value pairs per image for the project.",
                     "ru": "Максимальное количество пар ключ-значение в метаданных образа, всего на тенант."},
                  "value": 128},
                 {...}]

            }
        """
        customer = Customer.get_by_id(token.customer_id)
        return {"quota": customer.quota_info()}

    @post("customer/me/make_prod/")
    @check_params(
        token=CustomerTokenId
    )
    @autocommit
    def make_prod_self(self, token):
        """
        Set customer to production mode by current customer

        :return dict customer_info: Customer info.

        **Example**::

            {
                "customer_info": {
                    {"customer_id": 1,
                     "name": "John Doe",
                     "deleted": null,
                     "email": "customer@test.ru",
                     "birthday": "1990-10-17",
                     "country": "Russia",
                     "city": "Moscow",
                     "address": "Example street, 62",
                     "telephone": "8 (909) 515-77-07",
                     "created": "2015-04-24T11:14:22",
                     "blocked": false,
                     "customer_mode": "test",
                     "customer_type": "private",
                     "withdraw_period": "month",
                     "withdraw_date": "2015-07-01",
                     "email_confirmed": true,
                     "tariff_id": 2,
                     "currency": "USD",
                     "balance_limit": 0,
                     "os_tenant_id": 1,
                     "os_user_id": 1,
                     "promo_code": [{"value": "code_value_1"}, {"value": "code_value_2"}],
                     "account": {"rub": {"balance": "1035.22", "current": "1035.22", "withdraw": "0.00"}}
                     }
                }
            }

        """
        customer = Customer.get_by_id(token.customer_id)
        if not customer:
            raise errors.CustomerInvalidToken()

        if customer.customer_mode != Customer.CUSTOMER_TEST_MODE:
            logbook.debug("Customer {} is not in 'test' mode already. Nothing to do.", customer)
            return {'customer_info': display(customer)}

        if not customer.info or not customer.info.validate_production_fields():
            raise errors.ProductionModeNeedMoreInfo()

        comment = 'Process changing mode to production by customer.'
        customer.make_production(None, comment)
        return {'customer_info': display(customer)}

    @post("customer/<customer>/make_prod/", api_type=API_ADMIN)
    @check_params(
        token=TokenManager,
        customer=CustomerIdExpand,
        comment=String,
    )
    @autocommit
    def make_prod(self, token, customer, comment=None):
        """
        Set customer to production mode from admin panel.

        :param Customer customer: Customer id
        :param Str comment: Comment for changing customer to prod mode
        :return dict customer_info: Customer info.

        **Example**::

            {
                "customer_info": {
                    {"customer_id": 1,
                     "detailed_info": {
                        "name": "John Doe",
                        "birthday": "1990-10-17",
                        "country": "Russia",
                        "city": "Moscow",
                        "address": "Example street, 62",
                        "telephone": "8 (909) 515-77-07"
                     },
                     "deleted": null,
                     "email": "customer@test.ru",
                     "created": "2015-04-24T11:14:22",
                     "blocked": false,
                     "customer_mode": "test",
                     "customer_type": "private",
                     "withdraw_period": "month",
                     "withdraw_date": "2015-07-01",
                     "email_confirmed": true,
                     "tariff_id": 2,
                     "currency": "USD",
                     "balance_limit": 0,
                     "os_tenant_id": 1,
                     "os_user_id": 1,
                     "promo_code": [{"value": "code_value_1"}, {"value": "code_value_2"}],
                     "account": {"rub": {"balance": "1035.22", "current": "1035.22", "withdraw": "0.00"}}
                     }
                }
            }

        """
        if customer.customer_mode != Customer.CUSTOMER_TEST_MODE:
            logbook.debug("Customer {} is not in 'test' mode already. Nothing to do.", customer)
            return {'customer_info': display(customer)}

        if not customer.info or not customer.info.validate_production_fields():
            raise errors.ProductionModeNeedMoreInfo()

        customer.make_production(token.user_id, comment or "Process changing mode to production from admin panel")
        return {'customer_info': display(customer)}

    @delete('customer/password_reset/')
    @check_params(email=(Email, IndexSizeLimit))
    def request_password_reset(self, email):
        """
        Sent email with link to reset password

        :param Email email: Email_ - user email

        :return: None.
        """
        self.send_password_reset_email(email, request_base_url())
        return {}

    @post('customer/password_reset/<password_token>/')
    @check_params(password_token=CustomerPasswordResetTokenValidator, password=PasswordValidator)
    @autocommit
    def password_reset(self, password_token, password):
        """
        Reset customer password

        :param CustomerPasswordResetToken password_token:  Token which was returned by method
                :obj:`POST /0/customer/password_reset/ <view.POST /0/customer/password_reset>`;
        :param str password: New password.

        :return: None
        """
        # noinspection PyUnresolvedReferences
        customer = Customer.get_by_id(password_token.customer_id)
        customer.password_reset(password)
        CustomerToken.remove_by(customer.customer_id)
        CustomerPasswordResetToken.remove(password_token)
        return {}

    # noinspection PyUnusedLocal
    @get('customer/password_reset/<password_token>/')
    @check_params(password_token=CustomerPasswordResetTokenValidator)
    def validate_password_reset(self, password_token):
        """
        Checks that password reset token is valid.

        :param PasswordResetToken password_token: Token which was returned by method
                :obj:`POST /0/customer/password_reset/ <view.POST /0/customer/password_reset>`.

        :return: None.
        """
        return {}

    @staticmethod
    def send_password_reset_email(email, base_url):
        customer = Customer.get_by_email(email, include_deleted=False)
        if customer is None:
            raise errors.CustomerNotFound()
        token = CustomerPasswordResetToken.create(customer)
        url = urljoin(base_url, posixpath.join(CustomerApi.CABINET_FRONTEND_PATH,
                                               "set-password/{}".format(token.id)))
        template_id = MessageTemplate.CUSTOMER_PASSWORD_RESET
        subject, body = MessageTemplate.get_rendered_message(template_id, language=customer.locale_language(),
                                                             user_name=customer.get_name(), password_reset_url=url)
        CustomerHistory.reset_password_email(customer, "send email with password reset link")
        send_email.delay(email, subject, body)
        db.session.commit()
        return customer

    @get("customer/<customer>/history/", api_type=API_ADMIN)
    @check_params(
        token=TokenId,
        before=Date(),
        after=Date(),
        customer=CustomerIdExpand,
        limit=IntRange(10, 1000)
    )
    def get_history(self, customer, after=None, before=None, limit=100):
        """
        Returns customer profile history

        :param Date before: Returns events which were happened before this date
        :param Date after: Returns events which were happened after this date
        :param int limit: Number of changes in the return list
        :param Customer customer: Customer id

        :return List history: List of dict with history description


        Note. Currently the following events are supported: "created", "tariff", "deleted",
        "info", "block", "unblock", "reset_email", "reset_password", "confirm_email",
        "email_confirmed", "make_prod", "changed_quotas", "change_password"

        **Example**::

            {"history": [{
                "user":
                    {"name": "Super Admin", "user_id": 1},
                "snapshot": {
                    "address": "",
                    "withdraw_period": "month",
                    "country": "",
                    "customer_id": 1,
                    "birthday": "1999-01-01",
                    "city": "",
                    "name": "test customer",
                    "deleted": null,
                    "customer_mode": "test",
                    "customer_type": "private",
                    "email_confirmed": false,
                    "email": "email@email.ru",
                    "withdraw_date": "2015-07-01",
                    "blocked": false,
                    "tariff_id": 1,
                    "telephone": "8(999)999 99 99",
                    "currency": "rub",
                    "balance_limit": 0,
                    "os_user_id": null,
                    "os_tenant_id": null,
                    "subscription": {
                        "status": {"enable": true, "email": ["email@email.ru"]},
                        "billing": {"enable": true, "email": ["email@email.ru"]},
                        "news": {"enable": true, "email": ["email@email.ru"]}},
                    "created": "2015-06-18T14:51:22+00:00"
                },
                "comment": null,
                "event": "tariff",
                "localized_name": {
                    "en": "Customer's tariff was changed."
                    "ru": "Тариф заказчика изменен."
                },
                "date": "2015-06-18T14:51:24+00:00"
            },
            {...}
            ]}
        """

        return {"history": display(customer.get_history(after, before, limit))}

    @get("customer/me/os_login/")
    @check_params(token=CustomerTokenId)
    def get_horizon_auth(self, token):
        """ Method is checking if cookies is valid. If not, set up new cookies required to login in horizon
        """
        customer = Customer.get_by_id(token.customer_id)
        if not customer.email_confirmed:
            raise errors.CustomerEmailIsNotConfirmed()
        if customer.blocked:
            raise errors.CustomerBlocked()
        if not customer.os_user_id:
            raise errors.CustomerWithoutHorizonUser()

        csrftoken = bottle.request.get_cookie("csrftoken") or ""
        sessionid = bottle.request.get_cookie("sessionid") or ""
        horizon = horizon_wrapper.HorizonAuth(csrftoken, sessionid)
        cookies = horizon.login_os_user(customer.os_username, customer.os_user_password)

        for cookie_name, cookie_data in cookies.items():
            cookie_data["path"] = "/"
            # uses add_header instead set_cookie method, due to set_cookie method is required code staff to
            # get all cooke's attr and converting each attr to appropriate format.
            bottle.response.add_header("Set-Cookie", cookie_data.output(header=""))
        return {}

    @get("customer/me/os_token/")
    @check_params(token=CustomerTokenId)
    def get_openstack_auth(self, token):
        """Return customers token info for OpenStack authorization.

        **Example**

            {
                'metadata': {
                    'is_admin': 0,
                    'roles': ['abcabcabc']
                },
                'serviceCatalog': [...],
                'token': {
                    'audit_ids': ['aaaaa'],
                    'expires': '2015-11-13T13:15:34Z',
                    'id': 'abcabcabc',
                    'issued_at': '2015-11-13T12:15:34.900950',
                    'tenant': {
                        'description': '...',
                        'enabled': True,
                        'id': 'abcabcabc',
                        'name': '...'
                    }
                },
                'user': {
                    'id': 'abcabcabc',
                    'name': '...',
                    'roles': [{'name': '_member_'}],
                    'roles_links': [],
                    'username': 'abcabcabc'
                },
                'version': 'v2.0'
            }
        """
        customer = Customer.get_by_id(token.customer_id)
        if not customer.email_confirmed:
            raise errors.CustomerEmailIsNotConfirmed()
        if customer.blocked:
            raise errors.CustomerBlocked()
        if not customer.os_user_id:
            raise errors.CustomerWithoutHorizonUser()
        auth_info = openstack.get_auth_info(username=customer.os_username,
                                            password=customer.os_user_password,
                                            tenant_id=customer.os_tenant_id)
        return auth_info

    @post("customer/<customer>/report/", api_type=API_ADMIN)
    @check_params(
        token=TokenId,
        customer=CustomerIdExpand,
        start=DateHourBeforeNow(),
        finish=DateHourBeforeNow(),
        report_format=Choose(["json", "csv", "pdf", "tsv"]),
        report_type=Choose(["simple", "acceptance_act", "detailed"])
    )
    def report(self, customer, start, finish, report_format, report_type="simple"):
        """
        Asynchronous generate customer usage report for the period.

        :param Customer customer: Customer Id
        :param DateHour start: Start report period
        :param DateHour finish: End report period
        :param Str report_format: report format. Currently supported the following formats: json, csv, pdf, tsv
        :param Str report_type: Type of report. Currently supported simple: simple, acceptance_act, detailed

        This method returns report as is (content type is set depend on report format) when report is ready, or returns
        status of report task generation.

        **Example**::


            {
                "status": "in progress",
            }

        In the case when requested json report file, it is returned in report field.

        **Example**::

            {
                "status": "completed",
                "report": {
                    "report_range": {
                        "finish": "2015-05-01T00:00:00+00:00",
                        "start": "2015-03-20T09:00:00+00:00",
                    },
                    "tariffs": [
                        {
                            "name": "Tariff for customers",
                            "currency": "rub",
                            "total_cost": "72.54",
                            "usage": [
                                {
                                    "measure": "Gb*month",
                                    "name": "Volume",
                                    "total_usage_volume": "998.00",
                                    "total_cost": "4.03",
                                    "price": "2.91",
                                    "service_id": "storage.disk",
                                    "category": "Storage"
                                },
                                {
                                    "measure": "Gb*month",
                                    "name": "Volume",
                                    "total_usage_volume": "1996.00",
                                    "total_cost": "34.21",
                                    "price": "12.34",
                                    "service_id": "storage.image",
                                    "category": "Storage"
                                },
                                {
                                    "measure": "Gb*month",
                                    "name": "Volume",
                                    "total_usage_volume": "1996.00",
                                    "total_cost": "34.29",
                                    "price": "12.37",
                                    "service_id": "storage.volume",
                                    "category": "Storage"
                                }
                            ]
                        }
                    ],
                    "total": {
                        "rub": "72.54"
                    },
                    "customer": {
                        "name": null,
                        "email": "boss@example.com",
                        "locale": "ru_ru"
                    }
                }
            }



        """
        return self.customer_report(customer, start, finish, report_format, report_type)

    def customer_report(self, customer, start, finish, report_format, report_type):
        if not customer.email_confirmed:
            raise errors.CustomerEmailIsNotConfirmed()

        if start >= finish:
            raise errors.StartShouldBeEarlierFinish()

        if not Report.is_supported(report_type, report_format):
            raise errors.ReportFormatIsNotSupported()

        if report_type == "acceptance_act" and customer.customer_type != Customer.CUSTOMER_TYPE_LEGAL_ENTITY:
            raise errors.CustomerIsNotEntity()

        report_cache = ReportCache()
        report_id = CustomerReportId(customer.customer_id, start, finish, report_type, report_format, customer.locale)
        data = report_cache.get_report(report_id)

        if data:
            if report_format == "json":
                return {"status": "completed",
                        "report": json.loads(data.decode("utf-8"))}
            filename = Report.generate_file_name(customer.get_name(), start, finish, report_format, customer.locale)
            content_disposition = make_content_disposition(filename, bottle.request.environ.get('HTTP_USER_AGENT'))
            return bottle.HTTPResponse(body=data, content_type=Report.content_types[report_format],
                                       content_disposition=content_disposition)

        status = ReportTask().task_status(report_id)
        if not status:
            result = report_file_generate.delay(report_id)
            logbook.info("Created report_file task {} for {}".format(report_id, result.id))
            ReportTask().set(report_id, result.id)
            status = "started"
        return {"status": status}

    @staticmethod
    def validate_customer_production_info(detailed_info, customer_type=None):
        from model import PrivateCustomerInfo, EntityCustomerInfo
        customer_info = EntityCustomerInfo() if customer_type == Customer.CUSTOMER_TYPE_LEGAL_ENTITY \
            else PrivateCustomerInfo()
        for k, v in detailed_info.items():
            setattr(customer_info, k, v)
        return customer_info.validate_production_fields()

    @post("customer/me/report/", api_type=API_CABINET)
    @check_params(
        token=CustomerTokenId,
        customer=CustomerIdExpand,
        start=DateHourBeforeNow(),
        finish=DateHourBeforeNow(),
        report_format=Choose(["json", "csv", "pdf", "tsv"]),
        report_type=Choose(["simple", "acceptance_act", "detailed"])
    )
    def report_me(self, token, start, finish, report_format, report_type="simple"):
        """
        Asynchronous generate customer usage report for the period.

        :param DateHour start: Start report period
        :param DateHour finish: End report period
        :param Str report_format: report format. Currently supported the following formats: json, csv, pdf, tsv
        :param Str report_type: Type of report. Currently supported simple: simple, acceptance_act, detailed

        This method returns report as is (content type is set depend on report format) when report is ready, or returns
        status of report task generation.

        **Example**::


            {
                "status": "in progress",
            }

        In the case when requested json report file, it is returned in report field.

        """
        customer = Customer.get_by_id(token.customer_id)
        return self.customer_report(customer, start, finish, report_format, report_type)

    @post("customer/<customer>/_fake_usage/", api_type=API_ADMIN)
    @check_params(
        token=TokenId,
        customer=CustomerIdExpand,
        start=Date(),
        finish=Date(),
        service_id=StringWithLimits(max_length=100),
        resource_id=StringWithLimits(max_length=100),
        volume=Integer())
    @autocommit
    def fake_usage(self, customer, start, finish, service_id, resource_id, volume):
        """
        Add fake withdraw for test report generation

        :param Customer customer: Customer Id
        :param Date start: Start time of service usage
        :param Date finish: Finish time of service usage
        :param str service_id: Id of service (storage.disk, storage.volume, storage.image etc)
        :param resource_id: name of used service. For example disk1, disk2
        :param volume: Size of used resource. (Bytes for storage).

        :return: Int withdraw: Cost of fake withdraw
        """
        from model.account.customer import Customer
        return {"withdraw": Customer.fake_usage(customer, start, finish, service_id, resource_id, volume)}

    @staticmethod
    def display_grouped_quotas(customer, used_quotas):
        result = []
        customer_quotas_info = {k["limit_id"]: k for k in customer.quota_info()}
        for quotas_group_dict in conf.dashboard_quotas.groups:
            for quotas_group_name, quotas_group_list in quotas_group_dict.items():
                group_quotas_result = []
                for quota_name in quotas_group_list:
                    customer_qoute_info = customer_quotas_info.get(quota_name)
                    if quota_name in used_quotas and customer_qoute_info:
                        customer_qoute_info.update({"max_value": customer_qoute_info["value"],
                                                    "value": used_quotas.get(quota_name)})
                        group_quotas_result.append(customer_qoute_info)
                if group_quotas_result:
                    result.append({quotas_group_name: group_quotas_result})

        return result

    @get("customer/me/used_quotas/")
    @check_params(
        token=CustomerTokenId,
        force=Bool
    )
    def get_used_quotas(self, token, force=False):
        """
        Returns info about used resources in os.

        :param force: Force update the used quota for the customer. I.e. it run async task to update.
        New value will be available on next requests only.
        :return: dict used_quotas: Dict with info about used quotas
        :return: bool loading: true when quota cache is empty. Async request to openstack is processed
        :return: int ago: how many seconds ago used quoata was refreshed

        **Example**::

            {"loading": false,
             "ago": 132,
             "used_quotas": [
                {"server_group": [
                    {
                        "limit_id": "instances",
                        "localization_description": {
                            "en": "The maximum number of servers at any one time for the project.",
                            "ru": "Максимальное количество виртуальных серверов, всего на тенант."
                        },
                        "localized_measure": {
                            "en": "pcs.",
                            "ru": "шт."
                        },
                        "localized_name": {
                            "en": "Instances",
                            "ru": "Серверы"
                        },
                        "value": 2,
                        "max_value": 2
                    },
                    {
                        "max_value": 2,
                        "value": 10,
                        "limit_id": "server_groups",
                        "localized_description: {
                            "en": "The maximum number of server groups per server for the project.",
                            "ru": "Максимальное количество групп серверов (server groups), всего на тенант."
                        },
                        "localized_name": {
                            "en": "Server Groups",
                            "ru": "Группы серверов"
                        },
                        "localized_measure": {
                            "en": "pcs.",
                            "ru": "шт."
                        }
                    }
                ]},
                {"compute_group": [...]},
                {...}
            ]}
        """
        customer = Customer.get_by_id(token.customer_id)
        quotas, ago = customer.used_quotas(force)
        loading = False
        if quotas is None:
            # quotas are not in the cache
            quotas = {}
            loading = True
        return {'used_quotas': self.display_grouped_quotas(customer, quotas),
                'loading': loading,
                'ago': ago}

    @post("customer/<customer>/recreate_tenant/", api_type=API_ADMIN)
    @check_params(
        token=TokenManager,
        customer=CustomerIdExpand
    )
    @autocommit
    def recreated_tenant(self, customer):
        """
        Recreate tenant in Open Stack for specified customer

        :param Customer customer: Customer Id
        :return: None
        """
        if not customer.email_confirmed:
            raise errors.CustomerEmailIsNotConfirmed()

        task_os_create_tenant_and_user.delay(customer.customer_id, customer.email)

        return {}

    @delete('customer/payments/cloudpayments/card/')
    @check_params(token=CustomerTokenId, card_id=Integer)
    @autocommit
    def delete_card(self, token, card_id):
        """ Delete specified card from customer's payment cards.

        :param int card_id: Customer's card identifier
        :return: dict : Empty dictionary.

        **Example**::

            {}

        """
        CustomerCard.delete_card(card_id=card_id)
        return {}

    @get('customer/payments/cloudpayments/card/')
    @check_params(token=CustomerTokenId)
    def get_cards(self, token):
        """ Return customer's payment cards
        :return dict cards: Contains list of dicts with info about customer's cards.

        **Example**::

            {'cards': [
                {
                    'card_id': 1,
                    'card_type': 'Visa',
                    'last_four': '4242',
                    'status': 'active'
                }
            ]}

        """
        cards = display(CustomerCard.get_all_cards(customer_id=token.customer_id))
        return {'cards': cards}

    @put('customer/me/reset_os_password/')
    @check_params(token=CustomerTokenId)
    def reset_os_password(self, token):
        """
        Resets Openstack password

        :return: None
        """
        customer = Customer.get_by_id(token.customer_id)

        if customer.blocked:
            raise errors.CustomerBlocked()
        if not customer.os_user_id:
            raise errors.CustomerWithoutHorizonUser()

        reset_user_password.delay(customer.customer_id)
        return {}

    @get('customer/me/payments/auto_withdraw/')
    @check_params(token=CustomerTokenId)
    def auto_withdraw_get(self, token):
        """
        Returns auto withdraw parameters.

        **Example**::

            {
                'enabled': True,
                'balance_limit': 100,
                'payment_amount': 500
            }

        """
        customer = Customer.get_by_id(token.customer_id)
        return customer.display_auto_withdraw()

    @post('customer/me/payments/auto_withdraw/')
    @check_params(token=CustomerTokenId, enabled=Bool, balance_limit=Integer, payment_amount=PositiveInteger)
    @autocommit
    def auto_withdraw_change(self, token, enabled=None, balance_limit=None, payment_amount=None):
        """
        Change auto withdraw balance limit and payment amount.

        :param bool enabled: Enable or Disable auto withdraws
        :param int balance_limit: Balance limit to proceed auto payment
        :param int payment_amount: Payment amount
        :return: dict : Customer's auto withdraw params.

        **Example**::

            {
                'enabled': True,
                'balance_limit': 100,
                'payment_amount': 500
            }

        """
        customer = Customer.get_by_id(token.customer_id)
        customer.change_auto_withdraw(enabled, balance_limit, payment_amount)
        return customer.display_auto_withdraw()

    @get('customer/<customer>/payments/auto_withdraw/', api_type=API_ADMIN)
    @check_params(token=TokenManager, customer=CustomerIdExpand)
    def auto_withdraw_get_admin(self, token, customer):
        """ Returns auto withdraw parameters for specified customer.
        :param Customer customer: Customer Id

        :return: dict : Customer's auto withdraw params.

        **Example**::

        {
            'enabled': True,
            'balance_limit': 100,
            'payment_amount': 500
        }

        """
        return customer.display_auto_withdraw()

    @post('customer/<customer>/payments/auto_withdraw/', api_type=API_ADMIN)
    @check_params(token=TokenManager, customer=CustomerIdExpand,
                  enabled=Bool, balance_limit=Integer, payment_amount=PositiveInteger)
    @autocommit
    def auto_withdraw_change_admin(self, token, customer, enabled=None, balance_limit=None, payment_amount=None):
        """ Change auto withdraw balance limit and payment amount for specified customer

        :param bool enabled: Enable or Disable auto withdraws
        :param int balance_limit: Balance limit to proceed auto payment
        :param int payment_amount: Payment amount
        :return: dict : Customer's auto withdraw params.

        **Example**::

            {
                'enabled': True,
                'balance_limit': 100,
                'payment_amount': 500
            }

        """
        customer.change_auto_withdraw(enabled, balance_limit, payment_amount)
        return customer.display_auto_withdraw()

    @post('customer/me/invoice/')
    @check_params(token=CustomerTokenId,
                  date=DateTime(),
                  amount=DecimalMoney,
                  currency=ActiveCurrencies,
                  number=PositiveInteger
                  )
    def invoice_self(self, token, amount, currency=None, date=None, number=None):
        """
        Generate invoice for customer

        :param Money amount: Amount of invoice
        :param String currency: Currency of invoice (not mandatory, by default current customer tariff currency is used)
        :param Date date: Date of invoice (not mandatory, the current time is used by default)
        :param int number: Order Id (not mandatry, the gap will be used by default)

        :return: PDF file
        """
        customer = Customer.get_by_id(token.customer_id)

        return self.invoice(customer, amount, date, currency, number)


    @post('customer/<customer>/invoice/', api_type=API_ADMIN)
    @check_params(token=TokenManager,
                  customer=CustomerIdExpand,
                  date=DateTime(),
                  amount=DecimalMoney,
                  currency=ActiveCurrencies,
                  number=PositiveInteger
                  )
    def invoice_by_manager(self, customer, amount, currency=None, date=None, number=None):
        """
        Generate invoice for customer

        :param Id customer: Customer Id
        :param Money amount: Amount of invoice
        :param String currency: Currency of invoice (not mandatory, by default current customer tariff currency is used)
        :param Date date: Date of invoice (not mandatory, the current time is used by default)
        :param int number: Order Id (not mandatry, the gap will be used by default)

        :return: PDF file
        """
        return self.invoice(customer, amount, date, currency, number)

    def invoice(self, customer, amount, date=None, currency=None, number=None):
        date = date or utcnow().datetime
        rendered_pdf = customer.pdf_invoice(amount, date, currency, number)
        filename = Report.generate_file_name(customer.get_name(), date, None, "pdf")
        content_disposition = make_content_disposition(filename, bottle.request.environ.get('HTTP_USER_AGENT'))
        return bottle.HTTPResponse(body=rendered_pdf, content_type=Report.content_types["pdf"],
                                   content_disposition=content_disposition)

    @post('customer/me/payments/withdraw/')
    @check_params(token=CustomerTokenId,
                  amount=DecimalMoney(positive_only=True),
                  card_id=PositiveInteger)
    def withdraw_from_card(self, token, amount, card_id):
        """
            Withdraw customer for given amount
`
        :param Money amount: Amount of withdraw
        :param int card_id: Customers card identifier

        :return: dict: On success - customer card info.

        **Example**::

            {
                'enabled': True,
                'balance_limit': 100,
                'payment_amount': 500
            }

        """
        customer = Customer.get_by_id(token.customer_id)
        customer_card = CustomerCard.get_one(card_id, customer.customer_id)
        if not customer_card:
            raise errors.PaymentCardNotFound()

        PaymentService.manual_withdraw(customer, customer_card, amount)
        return display(customer_card)
