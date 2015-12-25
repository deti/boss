import conf
import errors
import json
import logbook
from datetime import timedelta
from model import db, AccountDb, duplicate_handle, Service, User, Category
from sqlalchemy import Column, ForeignKey, UniqueConstraint, desc, or_
from sqlalchemy.orm import relationship, deferred
from arrow import utcnow
from utils.i18n import DEFAULT_LANGUAGE
from utils import DateTimeJSONEncoder
from utils.money import decimal_to_string


class TariffLocalization(db.Model, AccountDb):
    language = Column(db.String(2), primary_key=True)
    parent_id = Column(db.Integer, ForeignKey("tariff.tariff_id"), primary_key=True)
    localized_name = Column(db.String(254))

    UniqueConstraint(localized_name, language, name="uix_tariff_localization")

    def __str__(self):
        return "<%s: %s>" % (self.language, self.localized_name)

    def __repr__(self):
        return str(self)

    @classmethod
    def create_localization(cls, language, value):
        l18n = cls()
        l18n.language = language
        l18n.localized_name = value
        return l18n


class ServicePrice(db.Model, AccountDb):
    service_id = Column(db.String(32), primary_key=True)
    price = Column(db.DECIMAL(precision=conf.backend.decimal.precision, scale=conf.backend.decimal.scale))
    tariff_id = Column(db.Integer, ForeignKey("tariff.tariff_id"), primary_key=True)
    need_changing = Column(db.Boolean())

    def __init__(self, service_id, price, need_changing=False):
        self.service_id = service_id
        self.price = price
        self.need_changing = need_changing

    def display(self, short=True):
        service = Service.get_by_id(self.service_id)

        return {"service": service.display(short), "price": decimal_to_string(self.price),
                "need_changing": self.need_changing}

    @property
    def service(self):
        # we can't do it by relationship, because some services
        # can be fixed services which are configured from config file
        return Service.get_by_id(self.service_id)


class Tariff(db.Model, AccountDb):
    id_field = "tariff_id"
    unique_field = "localized_name"

    tariff_id = Column(db.Integer, primary_key=True)
    localized_name = relationship("TariffLocalization", cascade="all")
    description = Column(db.Text())
    currency = Column(db.String(3))

    parent_id = Column(db.Integer, ForeignKey('tariff.tariff_id', ondelete='CASCADE'))
    parent = relationship('Tariff', remote_side=[tariff_id])

    deleted = Column(db.DateTime())
    created = Column(db.DateTime())
    modified = Column(db.DateTime())
    services = relationship("ServicePrice", cascade="save-update, merge, delete, delete-orphan")
    mutable = Column(db.Boolean())
    default = Column(db.Boolean(), index=True)

    history = relationship('TariffHistory', remote_side=[tariff_id], lazy="dynamic", cascade="all")

    display_fields = frozenset(["description", "created", "deleted",
                                "tariff_id", "parent_id", "mutable", "default",
                                "currency", "modified"])

    def __str__(self):
        return "<Tariff %s>" % self.name

    @property
    def name(self):
        return self.localized_name_as_dict()[DEFAULT_LANGUAGE].localized_name

    def localized_name_as_dict(self):
        return {localization.language: localization for localization in self.localized_name}

    def update_localized_name(self, localized_name):
        current = self.localized_name_as_dict()
        for language, value in localized_name.items():
            if language in current:
                current[language].localized_name = value
            else:
                self.localized_name.append(TariffLocalization.create_localization(language, value))

    def get_localized_name(self, language):
        localized_name = self.localized_name_as_dict()
        return (localized_name.get(language) or localized_name[DEFAULT_LANGUAGE]).localized_name

    @classmethod
    @duplicate_handle(errors.TariffAlreadyExists)
    def create_tariff(cls, localized_name, description, currency, parent_id=None, services=None):
        tariff = cls()
        tariff.description = description
        tariff.currency = currency.upper()
        tariff.parent_id = parent_id
        now = utcnow().datetime
        tariff.created = now
        tariff.modified = now
        tariff.deleted = None
        tariff.update_localized_name(localized_name)
        tariff.mutable = True
        if parent_id and not services:
            tariff.update_services(Tariff.get_by_id(parent_id).services)
        if services:
            tariff.update_services(services)
        db.session.add(tariff)
        db.session.flush()
        return tariff

    @duplicate_handle(errors.TariffAlreadyExists)
    def update(self, localized_name=None, description=None, services=None, currency=None):
        if not self.mutable:
            if services and self.services_to_change():
                return self.update_new_vm_services(services)
            raise errors.ImmutableTariff()
        if self.deleted:
            raise errors.RemovedTariff()
        if localized_name:
            self.update_localized_name(localized_name)
        if description:
            self.description = description
        if services:
            self.update_services(services)
        if currency:
            self.currency = currency.upper()
        if db.session.is_modified(self):
            self.modified = utcnow().datetime
            return True
        return False

    def services_as_dict(self, lower=False):
        lower_func = (lambda x: x.lower()) if lower else lambda x: x

        return {lower_func(service.service_id): service for service in self.services}

    def service_price(self, service_id):
        service_id = str(service_id)
        sp = self.services_as_dict(lower=True).get(service_id.lower())
        if not sp:
            logbook.warning("Tariff {} don't have service {}", self, service_id)
            return None
        return sp.price

    def services_to_change(self):
        return {service.service_id for service in self.services if service.need_changing}

    def service_ids(self):
        return {service.service_id for service in self.services}

    def flavors(self):
        services = set()
        for service_price in self.services:
            service = service_price.service
            if service.category_id == Category.VM:
                services.add(service.flavor.flavor_id)
        return frozenset(services)

    def update_new_vm_services(self, services):
        current_services = self.services_as_dict()
        services_to_update = self.services_to_change()
        for service in services:
            service_id = service['service_id']
            if service_id in services_to_update:
                current_services[service_id].price = service['price']
                current_services[service_id].need_changing = False

    def update_services(self, services):
        current_services = self.services_as_dict()
        new_services = set()
        for service in services:
            if isinstance(service, dict):
                service_id = service["service_id"]
                price = service["price"]
            else:
                service_id = service.service_id
                price = service.price

            if service_id in current_services:
                current_services[service_id].price = price
            else:
                self.services.append(ServicePrice(service_id, price))
            new_services.add(service_id)
        removed_services = set(current_services.keys()) - new_services
        if removed_services:
            logbook.debug("Remove services {} from tariff {}", removed_services, self)
            for service_id in removed_services:
                self.services.remove(current_services[service_id])

    def display(self, short=True):
        res = super().display(short)
        res["localized_name"] = {loc.language: loc.localized_name for loc in self.localized_name}
        if not short:
            res["services"] = [s.display() for s in self.services]

        # HACK to show used customers by request
        if isinstance(short, list):
            res["used"] = self.used()

        return res

    def display_for_customer(self):
        tariff_info = {
            "services": [s.display() for s in self.services],
            "localized_name": {loc.language: loc.localized_name for loc in self.localized_name}
        }
        return tariff_info

    def remove(self):
        if self.deleted:
            return False
        if self.used() > 0 or self.deferred_changes():
            raise errors.RemoveUsedTariff()
        self.deleted = utcnow().datetime
        return True

    def mark_immutable(self):
        if self.mutable:
            self.mutable = False
            self.modified = utcnow().datetime
            return True
        return False

    @classmethod
    def delete_by_prefix(cls, prefix, field=None):
        field = field or cls.unique_field
        if not field:
            raise Exception("Field for removing is not set")
        member = getattr(cls, field)
        if field == "localized_name":
            query = cls.query.join(Tariff.localized_name).\
                filter(TariffLocalization.localized_name.ilike("%{}%".format(prefix + "%")))
        else:
            query = cls.query.filter(member.like(prefix + "%"))

        query = query.filter(or_(cls.default == None, cls.default == False))
        ids = [tariff_id for tariff_id, in query.with_entities(cls.id_field)]
        if not ids:
            return 0
        ServicePrice.query.filter(ServicePrice.tariff_id.in_(ids)).delete(False)
        TariffHistory.query.filter(TariffHistory.tariff_id.in_(ids)).delete(False)
        TariffLocalization.query.filter(TariffLocalization.parent_id.in_(ids)).delete(False)
        return cls.query.filter(cls.tariff_id.in_(ids)).delete("fetch")

    @classmethod
    def get_default(cls):
        return cls.query.filter(cls.default == True)

    def make_default(self):
        if self.default:
            return
        if self.deleted:
            raise errors.RemovedTariff()
        if self.mutable:
            raise errors.MutableTariffCantBeDefault()
        self.get_default().update({"default": False})
        db.session.flush()
        self.default = True

    def used(self):
        from model import Customer
        """
        Returns number of customer who use this tariff
        """
        return Customer.query.filter(Customer.tariff_id == self.tariff_id, Customer.deleted == None).count()

    def deferred_changes(self):
        from model import Deferred
        """
        Returns number of usages in deferred changes
        """
        return Deferred.query.filter(Deferred.tariff_id == self.tariff_id).count()

    def get_history(self, date_before, date_after):
        history = self.history.filter(TariffHistory.tariff_id == self.tariff_id)
        if date_after:
            history = history.filter(TariffHistory.date > date_after)
        if date_before:
            history = history.filter(TariffHistory.date < date_before)

        return history.order_by(desc(TariffHistory.history_id))


class TariffHistory(db.Model, AccountDb):
    EVENT_CREATE = "create"
    EVENT_UPDATE = "update"
    EVENT_DELETE = "delete"
    EVENT_ASSIGN = "assign"
    EVENT_UNASSIGN = "unassign"
    EVENT_IMMUTABLE = "immutable"

    EVENTS = {EVENT_CREATE, EVENT_UPDATE, EVENT_DELETE}
    MAX_AGE_OF_UPDATES_TO_AUTO_COLLAPSE = timedelta(seconds=conf.backend.tariff.max_age_of_updates_to_auto_collapse)

    history_id = Column(db.Integer, primary_key=True)

    event = Column(db.String(16))
    user_id = Column(db.Integer, ForeignKey('user.user_id', ondelete="set null"))
    user = relationship("User")

    tariff_id = Column(db.Integer, ForeignKey('tariff.tariff_id'))
    tariff = relationship("Tariff")

    customer_id = Column(db.Integer, ForeignKey('customer.customer_id'))
    customer = relationship("Customer")

    date = Column(db.DateTime())
    snapshot = deferred(Column(db.Text()))

    display_fields = frozenset(("history_id", "user", "event", "date", "localized_name", "snapshot"))
    display_fields_short = frozenset(("history_id", "user", "event", "date", "localized_name"))
    extract_fields = {"user": User.display}

    def __str__(self):
        return "<TariffHistory '%s' %s by %s>" % (self.tariff.name, self.event, self.date)

    def __repr__(self):
        return str(self)

    @classmethod
    def create(cls, event, user_id, tariff, customer=None):
        history_item = cls()
        history_item.event = event
        history_item.user_id = user_id
        history_item.tariff = tariff
        history_item.customer = customer
        history_item.date = tariff.modified
        history_item.snapshot = json.dumps(tariff.display(short=True), cls=DateTimeJSONEncoder)
        db.session.add(history_item)
        db.session.flush()

        if event == cls.EVENT_UPDATE:
            history_item._reduce_history_of_update_operations()

        return history_item

    def _reduce_history_of_update_operations(self):
        query = self.query.filter(TariffHistory.history_id != self.history_id,
                                  TariffHistory.tariff_id == self.tariff_id,
                                  TariffHistory.event == self.EVENT_UPDATE,
                                  TariffHistory.user_id == self.user_id,
                                  TariffHistory.date <= self.date + timedelta(seconds=1),
                                  TariffHistory.date >= self.date - self.MAX_AGE_OF_UPDATES_TO_AUTO_COLLAPSE)
        n = query.delete(False)
        logbook.debug("Reduced {} history records for tariff {}", n, self.tariff)
        return n

    @property
    def localized_name(self):
        return conf.tariff.events.get(self.event)
