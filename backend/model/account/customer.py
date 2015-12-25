import conf
import errors
import logbook

from model import db, display, AccountDb, duplicate_handle, MessageTemplate, ScheduledTask
from memdb.token import CustomerToken
from sqlalchemy import Column, ForeignKey, UniqueConstraint, desc, Enum
from sqlalchemy.orm import relationship
# noinspection PyUnresolvedReferences
from passlib.hash import pbkdf2_sha256
from arrow import utcnow
from datetime import timedelta
from decimal import Decimal
from task.mail import send_email
from utils.i18n import language_from_locale, DEFAULT_LANGUAGE
from os_interfaces.openstack_wrapper import openstack
from model.account.time_state import TestPeriodOver, BlockCustomer
from service.payments import PaymentService
from collections import Counter
from memdb.quota import QuotaCache
from cinderclient.exceptions import Unauthorized


quota_cache = QuotaCache()


class Customer(db.Model, AccountDb):
    id_field = "customer_id"
    unique_field = "email"

    CUSTOMER_TYPE_PRIVATE_PERSON = "private"
    CUSTOMER_TYPE_LEGAL_ENTITY = "entity"

    CUSTOMER_PRODUCTION_MODE = "production"
    CUSTOMER_PENDING_PRODUCTION_MODE = "pending_prod"
    CUSTOMER_TEST_MODE = "test"

    OPENSTACK_DASHBOARD_HORIZON = "horizon"
    OPENSTACK_DASHBOARD_SKYLINE = "skyline"
    OPENSTACK_DASHBOARD_BOTH = "both"

    ALL_MODES = [CUSTOMER_TEST_MODE, CUSTOMER_PENDING_PRODUCTION_MODE, CUSTOMER_PRODUCTION_MODE]
    ALL_TYPES = [CUSTOMER_TYPE_PRIVATE_PERSON, CUSTOMER_TYPE_LEGAL_ENTITY]
    ALL_PANELS = [OPENSTACK_DASHBOARD_HORIZON, OPENSTACK_DASHBOARD_SKYLINE, OPENSTACK_DASHBOARD_BOTH]
    CUSTOMER_MODE = Enum(*ALL_MODES)
    CUSTOMER_TYPE = Enum(*ALL_TYPES)
    CUSTOMER_PANEL = Enum(*ALL_PANELS)

    customer_id = Column(db.Integer, primary_key=True)
    email = Column(db.String(254), nullable=False, unique=True)
    password = Column(db.String(100), nullable=False)
    deleted = Column(db.DateTime())
    created = Column(db.DateTime())
    email_confirmed = Column(db.Boolean)
    tariff_id = Column(db.Integer, ForeignKey("tariff.tariff_id"), index=True)
    blocked = Column(db.Boolean)
    customer_type = Column(CUSTOMER_TYPE, nullable=False, default=CUSTOMER_TYPE_PRIVATE_PERSON)
    customer_mode = Column(CUSTOMER_MODE, nullable=False)
    withdraw_period = Column(db.String(16))
    balance_limit = Column(db.DECIMAL(precision=conf.backend.decimal.precision, scale=conf.backend.decimal.scale))
    auto_withdraw_enabled = Column(db.Boolean)
    auto_withdraw_balance_limit = Column(db.Integer)
    auto_withdraw_amount = Column(db.Integer)

    locale = Column(db.String(32))

    tariff = relationship("Tariff")

    # Each customer has his own OpenStack tenant_id
    os_tenant_id = Column(db.String(32), ForeignKey("tenant.tenant_id"), nullable=True, unique=True, default=None)
    # Each customer has his own OpenStack User account
    os_user_id = Column(db.String(32), nullable=True, unique=True, default=None)
    # Each customer has his own OpenStack Password
    os_user_password = Column(db.String(100), nullable=True, default=None)
    os_username = Column(db.String(64), nullable=True, default=None)
    # OpenStack dashboard view
    os_dashboard = Column(CUSTOMER_PANEL, nullable=False, default=OPENSTACK_DASHBOARD_HORIZON)

    subscriptions = relationship("Subscription", lazy='dynamic')
    switches = relationship("SubscriptionSwitch", lazy='dynamic')
    quota = relationship("Quote", lazy='dynamic')

    display_fields = frozenset(["customer_id", "email", "created", "deleted",
                                "email_confirmed", "tariff_id", "blocked", "customer_mode",
                                "customer_type", "withdraw_period", "balance_limit",
                                "os_tenant_id", "os_user_id", "locale", "os_username", "os_dashboard"])
    accounts = relationship("Account", cascade="all, delete-orphan")
    accounts_history = relationship("AccountHistory", cascade="all, delete-orphan", lazy='dynamic')
    history = relationship("CustomerHistory", cascade="all, delete-orphan", lazy='dynamic')
    private_info = relationship("PrivateCustomerInfo", uselist=False, backref="customer", cascade="all, delete-orphan")
    entity_info = relationship("EntityCustomerInfo", uselist=False, backref="customer", cascade="all, delete-orphan")
    tenant = relationship("Tenant")
    tasks = relationship("ScheduledTask", cascade="all, delete-orphan")

    AUTO_REPORT_TASK = "auto_report"

    role = "customer"  # stab for logging

    def __str__(self):
        return "<Customer %s blocked:%s, deleted:%s>" % (self.email, self.blocked, self.deleted)

    @property
    def info(self):
        return self.private_info if self.customer_type == self.CUSTOMER_TYPE_PRIVATE_PERSON else self.entity_info

    @classmethod
    def password_hashing(cls, raw_password):
        return pbkdf2_sha256.encrypt(raw_password, rounds=conf.customer.salt_rounds, salt_size=10)

    def check_password(self, raw_password):
        if not self.password:
            return False
        return pbkdf2_sha256.verify(raw_password, self.password)

    @classmethod
    @duplicate_handle(errors.CustomerAlreadyExists)
    def new_customer(cls, email, password, creator_id, detailed_info=None, comment="New customer",
                     withdraw_period=None, make_prod=False, customer_type=None, promo_code=None, locale=None):
        from model import Tariff, Account, CustomerHistory

        customer = cls()
        customer.email = email
        customer.password = cls.password_hashing(password) if password else ""
        customer.deleted = None
        customer.created = utcnow().datetime
        customer.email_confirmed = False
        customer.blocked = False
        customer.customer_mode = cls.CUSTOMER_PRODUCTION_MODE if make_prod else cls.CUSTOMER_TEST_MODE
        customer.customer_type = customer_type if customer_type else cls.CUSTOMER_TYPE_PRIVATE_PERSON
        customer.withdraw_period = withdraw_period or conf.customer.default_withdraw_period
        customer.auto_withdraw_enabled = conf.payments.auto_withdraw_enable
        customer.auto_withdraw_balance_limit = conf.payments.auto_withdraw_balance_limit
        customer.auto_withdraw_amount = conf.payments.auto_withdraw_amount
        customer.locale = locale or conf.customer.default_locale
        customer.os_dashboard = conf.customer.default_openstack_dashboard

        default_tariff = Tariff.get_default().first()
        if not default_tariff:
            default_tariff = Tariff.query.filter_by(mutable=False).first() or Tariff.query.filter_by().first()
            if not default_tariff:
                raise errors.TariffNotFound()
        customer.tariff_id = default_tariff.tariff_id
        customer.balance_limit = conf.customer.balance_limits.get(default_tariff.currency,
                                                                  conf.customer.balance_limits.default)
        db.session.add(customer)
        db.session.flush()

        customer.init_subscriptions()
        template = 'customer' if make_prod else 'test_customer'
        customer.quota_init(template)
        customer.accounts.append(Account.create(default_tariff.currency, customer, creator_id, comment))

        if promo_code is not None:
            PromoCode.new_code(promo_code, customer.customer_id)

        CustomerHistory.new_customer(customer, creator_id, comment)
        if detailed_info:
            customer.create_info(customer.customer_type, detailed_info)
        auto_report_task = ScheduledTask(cls.AUTO_REPORT_TASK, customer.customer_id, customer.withdraw_period)
        db.session.add(auto_report_task)

        logbook.info("New customer created: {}", customer)
        if not make_prod:
            currency = customer.tariff.currency.upper()
            initial_balance = conf.customer.test_customer.balance.get(currency)
            logbook.debug("Initial balance for customer {}: {} {}", customer, initial_balance, currency)
            if initial_balance:
                customer.modify_balance(Decimal(initial_balance), currency, None, "Initial test balance")

        return customer

    def update_os_credentials(self, tenant_id, tenant_name, user_id, username, password):
        from model import Tenant
        """Update os_tenant_id and os_user_id for customer with given email address."""
        if self.os_tenant_id is not None and self.os_tenant_id != tenant_id and tenant_id:
            logbook.warning("Customer {} already has tenant in open stack {}. New value: {}",
                            self, self.os_tenant_id, tenant_id)
            old_tenant = Tenant.get_by_id(self.os_tenant_id)
            if old_tenant:
                old_tenant.mark_removed()
        if self.os_user_id is not None and self.os_user_id != user_id and user_id:
            logbook.warning("Customer {} already has user in open stack {}. New value: {}",
                            self, self.os_user_id, user_id)
        self.os_user_password = password
        if tenant_id is not None and self.os_tenant_id != tenant_id:
            logbook.info("Create tenant in db {} {}", tenant_id, tenant_name)
            Tenant.create(tenant_id, tenant_name)
        self.os_tenant_id = tenant_id
        self.os_user_id = user_id
        self.os_username = username

    def update_os_password(self, password):
        self.os_user_password = password
        db.session.flush()

    @classmethod
    def get_by_email(cls, email, include_deleted=False):
        query = cls.query.filter_by(email=email)
        if not include_deleted:
            query.filter_by(deleted=None)
        return query.first()

    @classmethod
    def get_by_id(cls, customer_id, include_deleted=False):
        query = cls.query.filter_by(customer_id=customer_id)
        if not include_deleted:
            query.filter_by(deleted=None)
        return query.first()

    @classmethod
    def login(cls, email, password):
        customer = cls.get_by_email(email)

        if customer is None:
            logbook.info("Customer {} is not found", email)
            raise errors.CustomerUnauthorized()
        if customer.deleted:
            logbook.info("Customer {} is deleted at {}", email, customer.deleted)
            raise errors.CustomerUnauthorized()

        if not customer.check_password(password):
            logbook.info("Password mismatch for customer {}", email)
            raise errors.CustomerUnauthorized()

        token = CustomerToken.create(customer)

        return token, customer

    @classmethod
    def filter_by_customer_type(cls, query_parameters, customer_info, query):
        from model import PrivateCustomerInfo
        customer_type = cls.CUSTOMER_TYPE_PRIVATE_PERSON if customer_info is PrivateCustomerInfo \
            else cls.CUSTOMER_TYPE_LEGAL_ENTITY
        query = query.outerjoin(customer_info).filter(cls.customer_type == customer_type)
        for k, v in query_parameters.items():
            if hasattr(cls, k):
                query = query.filter(getattr(cls, k) == v)
            elif k.endswith('_before'):
                query = query.filter(getattr(cls, k.partition('_before')[0]) < v)
            elif k.endswith('_after'):
                query = query.filter(getattr(cls, k.partition('_after')[0]) > v)
            elif hasattr(customer_info, k):
                query = query.filter_by(**{k: v})

        return query

    @classmethod
    def filter(cls, query_parameters, visibility=None):
        from model import PrivateCustomerInfo, EntityCustomerInfo
        limit = query_parameters.pop("limit")
        page = query_parameters.pop("page")
        sort = query_parameters.pop("sort", None)

        query = cls.query
        if visibility == "all":
            pass
        elif visibility == "visible":
            query = cls.query.filter(cls.deleted.is_(None))
        elif visibility == "deleted":
            query = cls.query.filter(cls.deleted.isnot(None))

        if query_parameters:
            tariff_ids = query_parameters.pop("tariff_ids", None)
            if tariff_ids:
                query = query.filter(cls.tariff_id.in_(tariff_ids))

            customer_type = query_parameters.get('customer_type')

            if customer_type == cls.CUSTOMER_TYPE_PRIVATE_PERSON:
                result_query = cls.filter_by_customer_type(query_parameters, PrivateCustomerInfo, query)
            elif customer_type == cls.CUSTOMER_TYPE_LEGAL_ENTITY:
                result_query = cls.filter_by_customer_type(query_parameters, EntityCustomerInfo, query)
            else:
                private_query = cls.filter_by_customer_type(query_parameters, PrivateCustomerInfo, query).all()
                entity_query = cls.filter_by_customer_type(query_parameters, EntityCustomerInfo, query).all()
                result_query = private_query + entity_query

            customer_ids = {item.customer_id for item in result_query}
            query = cls.query.filter(cls.customer_id.in_(customer_ids))

        if sort:
            query = cls.sort_query(query, sort)
        return query.paginate(page, limit)

    def update(self, new_common_params=None, new_info_params=None, user_id=None, comment=None):
        from model import CustomerHistory
        if self.deleted:
            raise errors.CustomerRemoved()

        if not (new_common_params or new_info_params):
            return

        if new_common_params:
            assert "tariff_id" not in new_common_params
            assert "tariff" not in new_common_params
            password = new_common_params.get("password")
            if password:
                new_common_params["password"] = self.password_hashing(password)
                CustomerHistory.change_password(self, comment)
            withdraw_period = new_common_params.get("withdraw_period")
            if withdraw_period:
                task = ScheduledTask.get_by_customer(self.customer_id, self.AUTO_REPORT_TASK)
                task.update_period(withdraw_period)
            super().update(new_common_params)

        if new_info_params:
            if not self.info:
                self.create_info(self.customer_type, new_info_params)
            else:
                self.info.update(new_info_params)

        CustomerHistory.change_info(self, user_id, comment)

    def update_tariff(self, new_tariff_id, user_id, comment=None):
        from model import Tariff, CustomerHistory
        from task.customer import change_flavors
        if self.deleted:
            raise errors.CustomerRemoved()

        new_tariff = Tariff.get_by_id(new_tariff_id)
        if new_tariff.mutable:
            raise errors.AssignMutableTariff()
        if new_tariff.deleted:
            raise errors.RemovedTariff()

        if self.tariff.currency != new_tariff.currency:
            # TODO implement logic
            pass
        logbook.info("Change tariff from {} to {} for customer {}", self.tariff, new_tariff, self)
        self.tariff_id = new_tariff_id
        if self.os_tenant_id:
            change_flavors.delay(self.os_tenant_id, new_tariff.flavors())
        CustomerHistory.tariff_changed(self, user_id, comment)

    def mark_removed(self):
        res = super().mark_removed()
        CustomerToken.remove_by(self.customer_id)
        ScheduledTask.remove_by_customer_id(self.customer_id)
        return res

    def password_reset(self, password):
        from model import CustomerHistory
        self.password = self.password_hashing(password)
        CustomerHistory.reset_password(self, "password was reset ed")

    def confirm_email(self):
        from model import CustomerHistory
        from task.openstack import task_os_create_tenant_and_user

        self.email_confirmed = True
        logbook.info("Email for customer {} confirmed", self)
        CustomerHistory.email_confirmed(self, "Email is confirmed")
        if self.customer_mode == self.CUSTOMER_TEST_MODE:
            TestPeriodOver.create(self.customer_id)

        db.session.commit()

        logbook.info("Creating tenants for customer {}", self)
        task_os_create_tenant_and_user.delay(self.customer_id, self.email)

    def get_deferred(self):
        from model.account.deferred import Deferred
        return Deferred.get_by_customer(self.customer_id)

    def account_dict(self):
        return {account.currency: {
                "balance": account.balance,
                "withdraw": account.withdraw,
                "current": account.current} for account in self.accounts}

    def balance_dict(self):
        return {account.currency: account.balance for account in self.accounts}

    def display(self, short=True):
        res = super().display(short)
        res["account"] = self.account_dict()
        res["currency"] = self.tariff.currency
        res["tariff_id"] = self.tariff_id
        auto_report_task = ScheduledTask.get_by_customer(self.customer_id, self.AUTO_REPORT_TASK)
        res["withdraw_date"] = auto_report_task.next_scheduled if auto_report_task else None
        res["detailed_info"] = self.info.display(short) if self.info else {}
        res["promo_code"] = display(PromoCode.get_by_customer_id(self.customer_id))
        return res

    def report_info(self):
        report_fields = ["email", "locale"]
        report_info = {field: getattr(self, field, None) for field in report_fields}

        report_info["name"] = self.get_name()
        entity_info = self.entity_info
        if entity_info:
            report_info["entity_info"] = entity_info.display()
        return report_info

    def get_account(self, currency):
        currency = currency.upper()
        for account in self.accounts:
            if account.currency == currency:
                return account
        return None

    def get_or_create_account(self, currency, user_id):
        from model import Account

        account = self.get_account(currency)
        if account:
            return account

        account = Account.create(currency, self, user_id)
        self.accounts.append(account)
        db.session.flush()
        return account

    def get_name(self):
        return self.info.name if self.info and self.info.name else self.email

    def check_balance(self, account, currency):
        if currency == self.tariff.currency:
            if not self.blocked and account.balance - account.withdraw < self.balance_limit:
                self.block(blocked=True, user_id=None, message='insufficient funds')
                return

            from model import CustomerHistory
            block_event = CustomerHistory.get_last_block_event(self)
            if self.blocked and account.balance - account.withdraw > self.balance_limit and not block_event.user_id:
                self.block(blocked=False, user_id=None, message='balance is positive')

    def is_test_mode(self):
        return self.customer_mode == self.CUSTOMER_TEST_MODE

    def modify_balance(self, account_delta, currency, user_id, comment, transaction_id=None, cleanup=False):
        logbook.info("Changing balance of {}: {} {} by user {} with comment {}",
                     self, account_delta, currency, user_id, comment)
        if Decimal(account_delta) > 0 and not cleanup:
            self.check_wait_production()
        if not currency:
            currency = self.tariff.currency
        currency = currency.upper()
        account = self.get_or_create_account(currency, user_id)
        account.modify(self, account_delta, user_id, comment, transaction_id=transaction_id)
        PaymentService.send_email_about_balance_modifying(self, account_delta, currency,
                                                          account.balance - account.withdraw, comment)
        self.check_balance(account, currency)
        db.session.flush()

    def withdraw(self, delta, currency=None):
        assert isinstance(delta, Decimal)
        assert delta >= 0
        currency = (currency or self.tariff.currency).upper()
        logbook.debug("Withdraw {} {} of {}", delta, currency, self)
        account = self.get_account(currency)
        if account is None:
            raise Exception("Customer %s doesn't have account in %s, but withdraw %s %s is required" %
                            (self, currency, delta, currency))
        account.charge(delta)
        self.check_balance(account, currency)
        db.session.flush()

    def change_auto_withdraw(self, enabled, balance_limit, payment_amount):
        if enabled is not None:
            self.auto_withdraw_enabled = enabled
        if payment_amount is not None:
            assert payment_amount > 0
            self.auto_withdraw_amount = payment_amount
        if balance_limit is not None:
            self.auto_withdraw_balance_limit = balance_limit

    def display_auto_withdraw(self):
        return {
            'enabled': self.auto_withdraw_enabled,
            'balance_limit': self.auto_withdraw_balance_limit,
            'payment_amount': self.auto_withdraw_amount
        }

    def get_account_history(self, after=None, before=None, limit=1000):
        from model import AccountHistory
        query = self.accounts_history.filter(AccountHistory.customer_id == self.customer_id)
        if after:
            query = query.filter(AccountHistory.date >= after)
        if before:
            query = query.filter(AccountHistory.date < before)
        query = query.order_by(desc(AccountHistory.account_history_id)).limit(limit)
        return query

    def check_account_history_transaction(self, transaction_id):
        from model import AccountHistory
        return self.accounts_history.filter(AccountHistory.customer_id == self.customer_id,
                                            AccountHistory.transaction_id == transaction_id).count()

    @classmethod
    def get_customers_by_prefix_info_field(cls, prefix, field):
        from model import PrivateCustomerInfo, EntityCustomerInfo

        if not field:
            raise Exception("Field for is not set")

        customers = []
        if getattr(PrivateCustomerInfo, field, None):
            query = cls.query.join(PrivateCustomerInfo).filter(cls.customer_type == cls.CUSTOMER_TYPE_PRIVATE_PERSON,
                                                               getattr(PrivateCustomerInfo, field).ilike(prefix + "%"))
            customers.extend(query.all())
        if getattr(EntityCustomerInfo, field, None):
            query = cls.query.join(EntityCustomerInfo).filter(cls.customer_type == cls.CUSTOMER_TYPE_LEGAL_ENTITY,
                                                              getattr(EntityCustomerInfo, field).ilike(prefix + "%"))
            customers.extend(query.all())
        return customers

    @classmethod
    def delete_by_prefix(cls, prefix, field=None):
        from model import Account, AccountHistory, Tenant
        from task.openstack import final_delete_from_os

        field = field or cls.unique_field
        if not field:
            raise Exception("Field for removing is not set")

        if getattr(cls, field, None):
            query = cls.query.filter(getattr(cls, field).like(prefix + "%"))
            ids = [customer_id for customer_id, in query.with_entities(cls.id_field)]
        else:
            ids = [item.customer_id for item in cls.get_customers_by_prefix_info_field(prefix, field)]

        if not ids:
            return 0
        logbook.info("Remove customers by prefix: {}", prefix)
        Subscription.query.filter(Subscription.customer_id.in_(ids)).delete(False)
        SubscriptionSwitch.query.filter(SubscriptionSwitch.customer_id.in_(ids)).delete(False)
        AccountHistory.query.filter(AccountHistory.customer_id.in_(ids)).delete(False)
        Account.query.filter(Account.customer_id.in_(ids)).delete(False)
        Quote.query.filter(Quote.customer_id.in_(ids)).delete(False)
        CustomerCard.query.filter(CustomerCard.customer_id.in_(ids)).delete(False)
        customers = cls.query.filter(cls.customer_id.in_(ids))
        if conf.devel.debug:
            logbook.debug("Remove customers {}", customers.all())

        tenants_ids = []
        for customer in customers:
            if customer.os_tenant_id:
                logbook.info("Final remove tenant {} for customer {}", customer.os_tenant_id, customer)
                final_delete_from_os.delay(customer.os_tenant_id, customer.os_user_id)
                tenants_ids.append(customer.os_tenant_id)
                customer.os_tenant_id = None
                customer.os_user_id = None
        if tenants_ids:
            Tenant.query.filter(Tenant.tenant_id.in_(tenants_ids)).delete(False)

        return customers.delete(False)

    def send_email_about_blocking(self, blocked, user_id):
        subscription_info = self.subscription_info()['status']
        if subscription_info['enable']:
            block_date = utcnow().datetime
            if blocked:
                if user_id:
                    template_id = MessageTemplate.CUSTOMER_BLOCKED_BY_MANAGER
                    subject, body = MessageTemplate.get_rendered_message(template_id, language=self.locale_language(),
                                                                         block_date=block_date, email=self.email)
                else:
                    template_id = MessageTemplate.CUSTOMER_BLOCKED
                    recommended_payment = conf.customer.minimum_recommended_payment.get(self.tariff.currency)
                    recommended_payment = {'money': Decimal(recommended_payment),
                                           'currency': self.tariff.currency}
                    subject, body = MessageTemplate.get_rendered_message(template_id, language=self.locale_language(),
                                                                         block_date=block_date, email=self.email,
                                                                         minimum_recomended_payment=recommended_payment)
            else:
                template_id = MessageTemplate.CUSTOMER_UNBLOCKED
                subject, body = MessageTemplate.get_rendered_message(template_id, language=self.locale_language())
            send_email.delay(subscription_info['email'], subject, body)

    def block(self, blocked, user_id, message=""):
        from model import CustomerHistory
        from task.openstack import block_user

        if self.blocked == blocked:
            return False

        logbook.debug("Customer {} is marked as {} because '{}'", self, "blocked" if blocked else "unblocked", message)
        self.blocked = blocked
        CustomerHistory.blocked(blocked, self, user_id, message)
        if self.os_user_id:
            block_user.delay(self.os_user_id, blocked)
            if self.customer_mode != self.CUSTOMER_TEST_MODE:
                if blocked:
                    BlockCustomer.create(self.customer_id)
                else:
                    BlockCustomer.stop(self.customer_id)

        self.send_email_about_blocking(blocked, user_id)

    def remove(self, user_id, comment):
        from model import CustomerHistory, Tenant
        from task.openstack import final_delete_from_os

        if not self.mark_removed():
            raise errors.CustomerRemoved()

        CustomerHistory.remove_customer(self, user_id, comment)
        if self.os_tenant_id or self.os_user_id:
            final_delete_from_os.delay(self.os_tenant_id, self.os_user_id)
        tenant_id = self.os_tenant_id
        self.update_os_credentials(None, None, None, None, None)
        Tenant.query.filter_by(tenant_id=tenant_id).delete(False)

    def get_history(self, after=None, before=None, limit=1000):
        from model import CustomerHistory
        query = self.history.filter(CustomerHistory.customer_id == self.customer_id)
        if after:
            query = query.filter(CustomerHistory.date >= after)
        if before:
            query = query.filter(CustomerHistory.date < before)
        query = query.order_by(desc(CustomerHistory.customer_history_id)).limit(limit)
        return query

    @classmethod
    def news_subscribers(cls):
        return cls.query.filter(cls.switches.any(name='news', enable=True))

    def subscription_info(self):
        subscriptions = self.subscriptions
        switches = self.switches

        result = {}

        for name in conf.subscription:
            subscription = subscriptions.filter(Subscription.name == name).all()
            switch = switches.filter(SubscriptionSwitch.name == name).one()
            emails = [s.email for s in subscription]
            result[name] = {'enable': switch.enable, 'email': emails}
        return result

    def subscriptions_update(self, data, user_id, comment=None):
        from model import CustomerHistory
        if self.deleted:
            raise errors.CustomerRemoved()

        subscriptions = self.subscriptions
        switches = self.switches
        for key, value in data.items():
            subscription = subscriptions.filter(Subscription.name == key)

            new_emails = set(value['email'])
            current_emails = {s.email for s in subscription}

            emails_to_add = new_emails - current_emails
            emails_to_delete = current_emails - new_emails

            if emails_to_add:
                for email in emails_to_add:
                    Subscription.new_subscription(name=key, email=email, customer_id=self.customer_id)
            if emails_to_delete:
                subscription.filter(Subscription.email.in_(emails_to_delete)).delete(False)

            switches.filter(SubscriptionSwitch.name == key).update({'enable': value["enable"]})
        CustomerHistory.change_info(self, user_id, comment)

    def init_subscriptions(self):
        for name in conf.subscription:
            if name in conf.customer.automatic_subscriptions:
                Subscription.new_subscription(name=name, email=self.email, customer_id=self.customer_id)
                SubscriptionSwitch.new_switch(name=name, enable=True, customer_id=self.customer_id)
            else:
                SubscriptionSwitch.new_switch(name=name, enable=False, customer_id=self.customer_id)

    def quota_info(self):
        quotas = self.quota
        return [quota.display() for quota in quotas]

    def quota_update(self, data, user_id):
        from task.customer import update_quota

        for name, value in data.items():
            self.quota.filter(Quote.name == name).update({'value': value})
        update_quota.delay(self.customer_id, user_id, data)

    def quota_init(self, template='test_customer'):
        for name, value in conf.template[template].items():
            Quote.new_quota(name=name, value=value, customer_id=self.customer_id)

    def make_production(self, user_id, comment):
        if not self.email_confirmed:
            raise errors.CustomerEmailIsNotConfirmed()
        account = self.get_account(self.tariff.currency)
        if account.current > self.balance_limit:
            self._make_prod(user_id, comment)
        else:
            self._make_pending_prod(user_id, comment)

    def check_wait_production(self):
        if self.customer_mode == self.CUSTOMER_PENDING_PRODUCTION_MODE:
            self._make_prod()

    def send_email_make_production(self):
        template_id = MessageTemplate.CUSTOMER_MAKE_PRODUCTION
        subject, body = MessageTemplate.get_rendered_message(template_id, language=self.locale_language())
        send_email.delay(self.email, subject, body)

    def _make_prod(self, user_id=None, comment=''):
        from model import CustomerHistory
        from task.customer import clean_up_customer_service_usage

        TestPeriodOver.stop(self.customer_id)
        account = self.get_account(self.tariff.currency)
        if account.current < 0:
            self.clean_up_balance(user_id)
        time_end = utcnow().datetime
        self.clean_up_service_usage(time_end)
        clean_up_customer_service_usage.apply_async((self.customer_id, time_end), eta=time_end + timedelta(hours=2))

        self.quota_update(conf.template['customer'], user_id)
        if self.blocked:
            self.block(blocked=False, user_id=user_id)
        openstack.change_tenant_quotas(self.os_tenant_id, **conf.template['customer'])
        self.update({'customer_mode': self.CUSTOMER_PRODUCTION_MODE})
        CustomerHistory.make_prod(self, user_id, comment)
        self.send_email_make_production()

    def _make_pending_prod(self, user_id, comment):
        from model import CustomerHistory

        TestPeriodOver.stop(self.customer_id)
        self.update({'customer_mode': self.CUSTOMER_PENDING_PRODUCTION_MODE})
        CustomerHistory.make_pending_prod(self, user_id, comment)

    def clean_up_balance(self, user_id=None):
        for currency, balance in self.balance_dict().items():
            self.modify_balance(-balance, currency, user_id,
                                'Customer balance is reset to 0.0 by system during switching to production mode',
                                cleanup=True)
        db.session.flush()

    def clean_up_service_usage(self, time_end):
        from model import ServiceUsage
        service_usages_to_clean = ServiceUsage.query.filter(ServiceUsage.tenant_id == self.os_tenant_id,
                                                            ServiceUsage.end <= time_end)
        total_cost = self.calculate_usage_cost(service_usages_to_clean.all())
        self.get_account(self.tariff.currency).charge(-total_cost)
        service_usages_to_clean.delete(False)

    @classmethod
    def get_by_tenant_id(cls, tenant_id):
        return cls.query.filter_by(os_tenant_id=tenant_id).first()

    def calculate_usage_cost(self, usages):
        from model import Service, Category, ServicePrice
        from task.notifications import notify_managers_about_new_service_in_tariff

        total_cost = Decimal()
        tariff = self.tariff
        if not tariff:
            raise Exception("Tariff is not set for customer %s" % self)

        services = tariff.services_as_dict(lower=True)
        for usage in usages:
            db.session.add(usage)
            service_id = usage.service_id.lower() if isinstance(usage.service_id, str) else str(usage.service_id)
            service_price = services.get(service_id)
            service = Service.get_by_id(service_id)

            usage.tariff_id = tariff.tariff_id
            usage.customer_mode = self.customer_mode

            if service is None:
                logbook.error("Not found declaration service {} during calculate usage for {}",
                              usage.service_id, self)
                continue

            usage_volume = service.calculate_volume_usage(usage)
            usage.usage_volume = usage_volume

            if service_price is None:
                if service.category_id == Category.VM:
                    if service.deleted:
                        logbook.error("Service {} not found in {} for {}. But this service is archived",
                                      service_id, tariff, self)
                    else:
                        service_price = ServicePrice(service_id=service_id, price=Decimal(0), need_changing=True)
                        self.tariff.services.append(service_price)
                        services = tariff.services_as_dict(lower=True)
                        flavor_name = Service.get_by_id(service_id).flavor.flavor_id
                        notify_managers_about_new_service_in_tariff.delay(self.customer_id, flavor_name)
                else:
                    logbook.warning("Service {} not found in {} for {}. Allowed services: {}",
                                    service_id, tariff, self, services.keys())

            if service_price:
                usage_cost = usage_volume * service_price.price / service.hours
            else:
                usage_cost = Decimal(0)
            total_cost += usage_cost
            usage.cost = usage_cost

        logbook.info("Found {} usages for customer {}. Total cost of used resources is: {}",
                     len(usages), self, total_cost)

        return total_cost

    def create_info(self, info_type: str, detailed_info):
        from model import PrivateCustomerInfo, EntityCustomerInfo
        if info_type == self.CUSTOMER_TYPE_PRIVATE_PERSON:
            self.private_info = PrivateCustomerInfo.create(self.customer_id, detailed_info)
        elif info_type == self.CUSTOMER_TYPE_LEGAL_ENTITY:
            self.entity_info = EntityCustomerInfo.create(self.customer_id, detailed_info)

    def locale_language(self):
        return language_from_locale(self.locale) or DEFAULT_LANGUAGE

    @classmethod
    def auto_withdraw_query(cls, email_prefix=None, now=None):
        query = None
        if email_prefix:
            query = cls.query.filter(cls.email.ilike("{}%".format(email_prefix)))
        query = ScheduledTask.scheduled_tasks(cls.AUTO_REPORT_TASK, now=now, query=query)
        return query

    @staticmethod
    def fake_usage(customer, start, finish, service_id, resource_id, volume, resource_name=None):
        from model import ServiceUsage
        from fitter.aggregation.timelabel import TimeLabel
        if customer.os_tenant_id is None:
            raise errors.TenantIsnotCreated()

        time_label = TimeLabel(start)
        finish_time_label = TimeLabel(finish)
        total_cost = Decimal(0)
        while time_label <= finish_time_label:
            st, fn = time_label.datetime_range()
            st = max(st, start)
            fn = min(fn, finish)
            service_usage = ServiceUsage(customer.os_tenant_id, service_id, time_label, resource_id,
                                         customer.tariff, volume, st, fn, resource_name=resource_name)
            db.session.add(service_usage)
            cost = customer.calculate_usage_cost([service_usage])
            customer.withdraw(cost)
            total_cost += cost
            time_label = time_label.next()
        return total_cost

    def pdf_invoice(self, amount, date, currency=None, number=None):
        from report.pdf_render import PdfRender

        entity_info = self.entity_info
        if entity_info is None:
            raise errors.CustomerIsNotEntity()
        number_str = str(number)
        if not number:
            number_str = "______"
            number = '<xpre>%s</xpre>' % number_str
        data = {"number": number,
                "number_str": number_str,
                "date": date,
                "currency": currency or self.tariff.currency,
                "amount": amount,
                "entity_info": entity_info,
                "nds": amount / Decimal(1.18) * Decimal(0.18)

                }
        data.update(conf.report.invoice)
        return PdfRender().render(data, "invoice", locale="ru_ru")

    @classmethod
    def customers_stat(cls):
        result = {"total": cls.query.count()}

        total_deleted = 0
        total_by_mode = Counter()
        total_blocked = 0
        for customer_type in cls.ALL_TYPES:
            query_by_type = cls.query.filter_by(customer_type=customer_type)
            for mode in cls.ALL_MODES:
                query = cls.query.filter_by(customer_mode=mode, customer_type=customer_type)
                metric_name = "%s_%s" % (mode, customer_type)
                count = query.count()
                total_by_mode[mode] += count
                result[metric_name] = count
                blocked = query.filter(cls.blocked.is_(True)).count()
                result[metric_name + "_blocked"] = blocked
                total_blocked += blocked

            deleted = query_by_type.filter(cls.deleted.isnot(None)).count()
            result[customer_type + "_deleted"] = deleted
            total_deleted += deleted
        result["total_deleted"] = total_deleted
        result["total_blocked"] = total_blocked
        for mode, count in total_by_mode.items():
            result["total_" + mode] = count

        return result

    def get_used_quotas(self):
        logbook.debug("Getting used quotas from openstack for {}", self)
        if self.os_tenant_id and not self.blocked:
            try:
                quotas = openstack.get_limits(self.os_tenant_id, self.os_username, self.os_user_password)
            except Unauthorized as e:
                logbook.warning("Customer {} is not blocked but can't sign in OpenStack account. Error message: {}",
                                self, e)
                quotas = {}
        else:
            quotas = {}

        if quotas:
            quota_cache.set(self, quotas)
        return quotas

    def used_quotas(self, force=False):
        from task.customer import get_used_quotas

        if not self.os_tenant_id:
            logbook.debug("Quotas are empty because tenant is not configured for {}", self)
            return {}, None

        if self.blocked:
            logbook.debug("Quotas are empty because {} is blocked", self)
            return {}, None

        quota = quota_cache.get(self)
        if not quota:
            logbook.debug("Quotas are missed in cache for {}", self)
            get_used_quotas.delay(self.customer_id)
            return None, None

        if quota.fresh:
            if force and quota.live_time > conf.customer.quota.min_live_time:
                get_used_quotas.delay(self.customer_id)
            return quota.used, quota.live_time

        get_used_quotas.delay(self.customer_id)
        return quota.used, quota.live_time

    @classmethod
    def active_tenants(cls):
        return [c.os_tenant_id for c in cls.query.filter(cls.os_tenant_id.isnot(None))]


class Subscription(db.Model, AccountDb):
    subscription_id = Column(db.Integer, primary_key=True)
    name = Column(db.String(16))
    email = Column(db.String(255))
    customer_id = Column(db.Integer, ForeignKey("customer.customer_id"))

    __table_args__ = (UniqueConstraint('customer_id', 'name', 'email'),)

    def __str__(self):
        return "<Subscription of %s to %s>" % (self.email, self.name)

    def __repr__(self):
        return str(self)

    @classmethod
    @duplicate_handle(errors.SubscriptionAlreadyExists)
    def new_subscription(cls, name, email, customer_id):
        subscription = cls()
        subscription.name = name
        subscription.email = email
        subscription.customer_id = customer_id

        db.session.add(subscription)
        return subscription


class SubscriptionSwitch(db.Model):
    confirmation_id = Column(db.Integer, primary_key=True)
    enable = Column(db.Boolean)
    name = Column(db.String(16))
    customer_id = Column(db.Integer, ForeignKey("customer.customer_id"))

    __table_args__ = (UniqueConstraint('customer_id', 'name'),)

    def __str__(self):
        return "<SubscriptionSwitch to %s>" % self.name

    def __repr__(self):
        return str(self)

    @classmethod
    @duplicate_handle(errors.SubscriptionSwitchAlreadyExists)
    def new_switch(cls, enable, name, customer_id):
        switch = cls()
        switch.name = name
        switch.enable = enable
        switch.customer_id = customer_id

        db.session.add(switch)
        return switch


class Quote(db.Model):
    quote_id = Column(db.Integer, primary_key=True)
    name = Column(db.String(32))
    value = Column(db.Integer)
    customer_id = Column(db.Integer, ForeignKey("customer.customer_id"))

    __table_args__ = (UniqueConstraint('customer_id', 'name'),)

    def __str__(self):
        return "<Quote %s with value %s>" % (self.name, self.value)

    def __repr__(self):
        return str(self)

    @classmethod
    @duplicate_handle(errors.QuotaAlreadyExist)
    def new_quota(cls, name, value, customer_id):
        quota = cls()
        quota.name = name
        quota.value = value
        quota.customer_id = customer_id

        db.session.add(quota)
        return quota

    def display(self):
        return {
            "limit_id": self.name,
            "localized_description": conf.quotas.all[self.name].get("localized_description", {}),
            "localized_name": conf.quotas.all[self.name].get("localized_name", {}),
            "localized_measure": conf.quotas.all[self.name].get("localized_measure", {}),
            "value": self.value
        }


class CustomerCard(db.Model, AccountDb):
    STATUS_ACTIVE = 0
    STATUS_DISABLED = 1
    STATUS_INVALID = 2

    status_info = {
        STATUS_ACTIVE: 'active',
        STATUS_INVALID: 'invalid',
        STATUS_DISABLED: 'disabled'}

    card_id = Column(db.Integer, primary_key=True)
    last_four = Column(db.String(4))
    card_type = Column(db.String(16))
    status = Column(db.Integer)
    token = Column(db.String(64))
    customer_id = Column(db.Integer, ForeignKey("customer.customer_id"))
    deleted = Column(db.DateTime())

    display_fields = frozenset(["card_id", "last_four", "card_type"])

    def __str__(self):
        return "<Customer card id:%s %s %s deleted:%s>" % (self.card_id, self.card_type, self.last_four, self.deleted)

    def display(self, short=True):
        res = super().display(short)
        res["status"] = self.status_info[self.status]
        return res

    @classmethod
    @duplicate_handle(errors.CustomerPaymentCardAlreadyExists)
    def add_card(cls, customer_id, last_four, card_type, token, active=False):
        new_card = cls()
        new_card.last_four = last_four
        new_card.card_type = card_type
        new_card.token = token
        new_card.customer_id = customer_id
        new_card.deleted = None
        if active:
            new_card.status = cls.STATUS_ACTIVE
            card = cls.get_active_card(customer_id)
            if card:
                card.status = cls.STATUS_DISABLED
        else:
            new_card.status = cls.STATUS_DISABLED

        db.session.add(new_card)
        return new_card

    @classmethod
    def delete_card(cls, card_id):
        card = cls.get_by_id(card_id)
        if not card:
            raise errors.NotFound
        if card.deleted is not None:
            raise errors.PaymentCardRemoved
        card.deleted = utcnow().datetime

    @classmethod
    def get_all_cards(cls, customer_id, include_deleted=False):
        query = CustomerCard.query.filter_by(customer_id=customer_id)
        if not include_deleted:
            query = query.filter_by(deleted=None)
        return query

    @classmethod
    def get_one(cls, card_id, customer_id=None, include_deleted=False):
        query = CustomerCard.query.filter_by(card_id=card_id)
        if customer_id:
            query = query.filter_by(customer_id=customer_id)
        if not include_deleted:
            query = query.filter_by(deleted=None)
        return query.first()

    @classmethod
    def get_active_card(cls, customer_id, include_deleted=False):
        query = cls.get_all_cards(customer_id, include_deleted).filter_by(status=CustomerCard.STATUS_ACTIVE)
        return query.first()

    def enable(self):
        if self.status != self.STATUS_ACTIVE:
            self.status = self.STATUS_ACTIVE
        return self

    def change_status(self, new_status):
        if self.deleted:
            raise errors.PaymentCardRemoved
        if new_status not in [CustomerCard.STATUS_ACTIVE,
                              CustomerCard.STATUS_DISABLED,
                              CustomerCard.STATUS_INVALID]:
            return
        self.status = new_status


class PromoCode(db.Model, AccountDb):
    promocode_id = Column(db.Integer, primary_key=True)
    value = Column(db.String(32))
    customer_id = Column(db.Integer, ForeignKey("customer.customer_id", ondelete="CASCADE"), index=True)

    display_fields = frozenset(["value"])

    def __str__(self):
        return "<PromoCode card %s customer_id:%s>" % (self.value, self.customer_id)

    @classmethod
    def new_code(cls, value, customer_id):
        promocode = cls()
        promocode.value = value
        promocode.customer_id = customer_id
        db.session.add(promocode)

    @classmethod
    def get_by_customer_id(cls, customer_id):
        return cls.query.filter_by(customer_id=customer_id)
