import conf
import errors
import logbook
from model import DisplayedModel, AccountDb, db, duplicate_handle
from utils.i18n import available_languages, DEFAULT_LANGUAGE
from functools import lru_cache
from sqlalchemy import Column, ForeignKey, UniqueConstraint, Enum
from sqlalchemy.orm import relationship
from arrow import utcnow
from os_interfaces.openstack_wrapper import openstack
from novaclient.exceptions import NotFound


@lru_cache()
def _default_localized_name(name):
    return {lang: name for lang in available_languages()}


class BaseService:
    measure = None

    @property
    def rate(self):
        return self.measure.rate

    @property
    def hours(self):
        return self.measure.hour_rate

    def calculate_volume_usage(self, service_usage):
        volume = service_usage.volume
        rate = self.rate
        if rate == 1:
            return volume
        return (volume + rate - 1) // rate

    @property
    def fixed(self):
        return False


class Measure(DisplayedModel):
    TIME = "time"
    QUANTITATIVE = "quant"
    TIME_QUANTITATIVE = "time_quant"
    TYPES = (TIME, QUANTITATIVE, TIME_QUANTITATIVE)

    display_fields = frozenset(["measure_id", "localized_name", "measure_type"])

    def __init__(self, measure_id):
        measure = None
        measure_type = None
        for measure_type in self.TYPES:
            measure = conf.service.measure[measure_type].get(measure_id)
            if measure:
                break

        if not measure:
            raise Exception("Measure %s not found" % measure_id)

        self.measure_id = measure_id
        self.measure_type = measure_type
        self.localized_name = measure.get("localized_name")
        if not self.localized_name:
            self.localized_name = _default_localized_name(measure_id)
        if measure_type == self.TIME_QUANTITATIVE:
            time = self.get(measure["time"])
            quant = self.get(measure["quantitative"])
            self.rate = measure.get("rate", quant.rate)
            self.hour_rate = measure.get("rate", time.hour_rate)
        else:
            self.rate = measure.get("rate", 1)
            self.hour_rate = measure.get("hour_rate", 1)

    @classmethod
    @lru_cache()
    def get(cls, name):
        return cls(name)

    def __str__(self):
        return self.measure_id

    def __repr__(self):
        return str(self)

    @classmethod
    def list(cls, measure_type=None):
        for typ in cls.TYPES:
            if measure_type and measure_type != typ:
                continue

            for measure_id in conf.service.measure[typ]:
                yield cls.get(measure_id)

    def get_localized_name(self, language):
        localized_name = self.localized_name
        return localized_name.get(language) or localized_name[DEFAULT_LANGUAGE]


class Category(DisplayedModel):
    display_fields = frozenset(["category_id", "localized_name"])
    CUSTOM = "custom"
    VM = "vm"

    def __init__(self, category_id, localized_name, services, measure):
        self.category_id = category_id
        if not localized_name:
            localized_name = _default_localized_name(category_id)
        self.localized_name = localized_name
        self.services = services
        self.measure = measure

    @classmethod
    @lru_cache(1)
    def list(cls):
        categories = {}
        for category_id, data in conf.service.service.copy().items():
            localized_name = data.pop("localized_name", None)
            measure = data.pop("measure", None)
            categories[category_id] = cls(category_id, localized_name, data, measure)
        return categories

    def __str__(self):
        return self.category_id

    @classmethod
    def get_by_id(cls, category_id):
        return cls.list()[category_id]

    def get_localized_name(self, language):
        localized_name = self.localized_name
        return localized_name.get(language) or localized_name[DEFAULT_LANGUAGE]


class ServiceLocalization(db.Model, AccountDb):
    language = Column(db.String(2), primary_key=True)
    service_id = Column(db.Integer, ForeignKey("service.service_id"), primary_key=True)
    localized_name = Column(db.String(254))

    UniqueConstraint(localized_name, language, name="uix_service_localization")

    def __str__(self):
        return "<%s: %s>" % (self.language, self.localized_name)

    @classmethod
    def create_localization(cls, language, value):
        l18n = cls()
        l18n.language = language
        l18n.localized_name = value
        return l18n


class ServiceDescription(db.Model, AccountDb):
    language = Column(db.String(2), primary_key=True)
    service_id = Column(db.Integer, ForeignKey("service.service_id"), primary_key=True)
    localized_description = Column(db.String(254))

    def __str__(self):
        return "<%s: %s>" % (self.language, self.localized_description)

    @classmethod
    def create_localization(cls, language, value):
        l18n = cls()
        l18n.language = language
        l18n.localized_description = value
        return l18n


class Flavor(db.Model, AccountDb):
    display_fields = ("flavor_id", "vcpus", "ram", "disk", "network")

    service_id = Column(db.Integer, ForeignKey('service.service_id'))
    flavor_id = Column(db.String(32), primary_key=True)
    vcpus = Column(db.Integer)
    ram = Column(db.Integer)
    disk = Column(db.Integer)
    network = Column(db.Integer)

    @classmethod
    @duplicate_handle(errors.FlavorAlreadyExists)
    def new_flavor(cls, service_id, flavor_id, vcpus, ram, disk, network=None):
        flavor = cls()
        flavor.flavor_id = flavor_id
        flavor.service_id = service_id
        flavor.vcpus = vcpus
        flavor.ram = ram
        flavor.disk = disk
        flavor.network = network

        db.session.add(flavor)
        db.session.flush()

        return flavor

    def __str__(self):
        params = {'vcpus': self.vcpus,
                  'ram': self.ram,
                  'disk': self.disk,
                  'flavor_id': self.flavor_id}

        return ", ".join("%s: %s" % k_v for k_v in params.items())

    @duplicate_handle(errors.FlavorAlreadyExists)
    def update(self, parameters):
        super().update(parameters)

    @classmethod
    def get_service_id(cls, flavor_id):
        flavor = cls.query.get(flavor_id)
        if flavor is not None:
            return flavor.service_id
        else:
            raise errors.FlavorNotFound()


class Service(db.Model, AccountDb, BaseService):
    service_id = Column(db.Integer, primary_key=True)
    localized_name = relationship("ServiceLocalization", cascade="all")
    description = relationship("ServiceDescription", cascade="all")
    measure_id = Column(db.String(32))
    category_id = Column(Enum(Category.CUSTOM, Category.VM))
    mutable = Column(db.Boolean())
    deleted = Column(db.DateTime())

    flavor = relationship("Flavor", uselist=False, backref="service", cascade="all, delete-orphan")

    display_fields = ("service_id", "mutable", "deleted", "fixed")
    unique_field = "localized_name"
    id_field = "service_id"

    @classmethod
    @duplicate_handle(errors.ServiceAlreadyExisted)
    def create_service(cls, localized_name, category, measure, description=None, mutable=True):
        assert isinstance(measure, Measure)

        if measure.measure_type != Measure.TIME:
            raise Exception("Custom services can have only time measure")
        service = cls()
        service.update_localized_name(localized_name)
        if description:
            service.update_description(description)
        service.measure_id = measure.measure_id
        service.mutable = mutable
        service.category_id = category

        db.session.add(service)
        db.session.flush()

        return service

    @classmethod
    def create_vm(cls, localized_name, description=None, flavor_info=None, mutable=True):
        measure = Measure('hour')
        service = Service.create_service(localized_name, Category.VM, measure, description, mutable)

        service.flavor = Flavor.new_flavor(service.service_id, **flavor_info)

        return service

    @classmethod
    def create_custom(cls, localized_name, measure, description=None,):
        service = Service.create_service(localized_name, Category.CUSTOM, measure, description)
        return service

    def localized_name_as_dict(self):
        return {localization.language: localization for localization in self.localized_name}

    def description_as_dict(self):
        return {description.language: description for description in self.description}

    def get_localized_name(self, language):
        localized_name = self.localized_name_as_dict()
        return localized_name.get(language).localized_name or localized_name[DEFAULT_LANGUAGE]

    def update_localized_name(self, localized_name):
        current = self.localized_name_as_dict()
        for language, value in localized_name.items():
            if language in current:
                current[language].localized_name = value
            else:
                self.localized_name.append(ServiceLocalization.create_localization(language, value))

    def update_description(self, localized_description):
        current = self.description_as_dict()
        for language, value in localized_description.items():
            if language in current:
                current[language].localized_description = value
            else:
                self.description.append(ServiceDescription.create_localization(language, value))

    @classmethod
    def list(cls, only_categories=None, visibility=None):
        result = []

        query = cls.query
        if visibility == "all":
            pass
        elif visibility == "visible":
            query = cls.query.filter(cls.deleted == None)
        elif visibility == "deleted":
            query = cls.query.filter(cls.deleted != None)

        if not only_categories:
            result.extend(query)
        else:
            if Category.CUSTOM in only_categories:
                result.extend(query.filter(cls.category_id == Category.CUSTOM))
            if Category.VM in only_categories:
                result.extend(query.filter(cls.category_id == Category.VM))
        if visibility != 'deleted':
            result.extend(FixedService.list(only_categories))
        return result

    @classmethod
    def get_by_id(cls, service_id):
        try:
            # if service_id is int
            service_id = int(service_id)
            return super().get_by_id(service_id)
        except ValueError:
            pass

        return FixedService.get_by_id(service_id)

    def display(self, short=True):
        res = super().display(short)
        res["category"] = self.category.display()
        res["measure"] = self.measure.display()
        res["localized_name"] = {loc.language: loc.localized_name for loc in self.localized_name}
        res["description"] = {description.language: description.localized_description
                              for description in self.description}
        if self.category_id == Category.VM:
            res["flavor"] = self.flavor.display()

        return res

    @duplicate_handle(errors.ServiceAlreadyExisted)
    def update_names(self, localized_name=None, description=None):
        if self.deleted:
            raise errors.RemovedService()

        if localized_name:
            self.update_localized_name(localized_name)
        if description:
            self.update_description(description)

        return True

    def update_custom(self, localized_name=None, description=None, measure=None):
        if not self.mutable and measure:
            raise errors.ImmutableService()

        self.update_names(localized_name, description)

        if measure:
            if measure.measure_type != Measure.TIME:
                raise Exception("Custom services can have only time measure")
            self.measure_id = measure.measure_id

    def update_vm(self, localized_name=None, description=None, flavor_info=None):
        if not self.mutable and flavor_info:
            raise errors.ImmutableService()

        self.update_names(localized_name=localized_name, description=description)

        if flavor_info:
            self.flavor.update({k: v for k, v in flavor_info.items() if v is not None})

    @property
    def measure(self):
        return Measure(self.measure_id)

    @property
    def category(self):
        return Category.get_by_id(self.category_id)

    def mark_immutable(self):
        from task.openstack import create_flavor

        if self.deleted:
            raise errors.RemovedService()
        if self.mutable:
            self.mutable = False
            if self.category_id == Category.VM:
                vm = self.flavor
                try:
                    flavor = openstack.get_nova_flavor(vm.flavor_id)
                    logbook.info("Flavor {} already exists in OpenStack", vm.flavor_id)
                    if vm.vcpus != flavor.vcpus:
                        logbook.info("Flavor {} has different vcpus value(DB: {}, OS: {}). Changing DB value.",
                                     vm.flavor_id, vm.vcpus, flavor.vcpus)
                        self.flavor.vcpus = flavor.vcpus
                    if vm.ram != flavor.ram:
                        logbook.info("Flavor {} has different ram value(DB: {}, OS: {}). Changing DB value.",
                                     vm.flavor_id, vm.ram, flavor.ram)
                        self.flavor.ram = flavor.ram
                    if vm.disk != flavor.disk:
                        logbook.info("Flavor {} has different disk value(DB: {}, OS: {}). Changing DB value.",
                                     vm.flavor_id, vm.disk, flavor.disk)
                        self.flavor.disk = flavor.disk
                except NotFound:
                    create_flavor.delay(vm.flavor_id, vm.vcpus, vm.ram, vm.disk, is_public=False)

            return True
        return False

    def used(self):
        from model import Tariff, ServicePrice
        """
        Returns number of tariffs with this service.
        """

        return Tariff.query.filter(ServicePrice.service_id == self.service_id,
                                   Tariff.deleted == None,
                                   Tariff.tariff_id == ServicePrice.tariff_id).count()

    def remove(self):
        if self.deleted:
            raise errors.RemovedService()
        if self.used() > 0:
            raise errors.RemovingUsedService()
        self.deleted = utcnow().datetime
        return True

    @classmethod
    def delete_by_prefix(cls, prefix, field=None):
        field = field or cls.unique_field
        if not field:
            raise Exception("Field for removing is not set")
        member = getattr(cls, field, None)
        if member:
            if field == "localized_name":
                query = cls.query.join(Service.localized_name).\
                    filter(ServiceLocalization.localized_name.ilike("%{}%".format(prefix + "%")))
            else:
                query = cls.query.filter(member.like(prefix + "%"))
            ids = [service_id for service_id, in query.with_entities(cls.service_id)]
        else:
            ids = [flavor.service_id for flavor in Flavor.query.filter(getattr(Flavor, field).ilike(prefix+"%"))]
        if not ids:
            return 0
        ServiceLocalization.query.filter(ServiceLocalization.service_id.in_(ids)).delete(False)
        ServiceDescription.query.filter(ServiceDescription.service_id.in_(ids)).delete(False)
        Flavor.query.filter(Flavor.service_id.in_(ids)).delete(False)
        return cls.query.filter(cls.service_id.in_(ids)).delete(False)


class FixedService(DisplayedModel, BaseService):
    display_fields = ("service_id", "localized_name", "category", "measure", "mutable", "deleted", "description")
    expand_fields = frozenset(("category", "measure"))

    def __init__(self, service_id, data, category, base_measure=None):
        self.service_id = service_id
        self.data = (data or {}).copy()
        self.measure = Measure(self.data.pop("measure", base_measure))
        self.category = category
        self.category_id = category.category_id
        self.localized_name = self.data.pop("localized_name", None)
        if not self.localized_name:
            self.localized_name = _default_localized_name(self.service_id)
        self.description = self.data.pop("description", {})
        self.mutable = False
        self.deleted = None

    def __str__(self):
        return "<Service {0.service_id} {0.measure}>".format(self)

    @classmethod
    def all_services(cls):
        return {service.service_id.lower(): service for service in cls.list()}

    @classmethod
    @lru_cache()
    def list(cls, only_categories=None):
        result = []
        for category in Category.list().values():
            if only_categories and category.category_id not in only_categories:
                continue
            for service_id, service_data in category.services.items():
                result.append(cls(service_id, service_data, category, category.measure))
        return result

    @classmethod
    def get_by_id(cls, service_id):
        return cls.all_services().get(service_id.lower())

    def get_localized_name(self, language):
        localized_name = self.localized_name
        return localized_name.get(language) or localized_name[DEFAULT_LANGUAGE]

    @property
    def fixed(self):
        return True
