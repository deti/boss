import logbook
from fitter.aggregation.timelabel import TimeLabel
from model import Service, Customer, ServiceUsage, Tariff, Measure, Category
from report import CustomerReport, Serialized
from report.simple import TariffReport as _TariffReport, ServiceReport as SimpleServiceReport
from collections import Counter
from utils import cached_property, timed
from utils.money import decimal_to_string
from operator import attrgetter
from decimal import Decimal


class ResourceUsageBase(Serialized):
    json_fields = ["start", "finish", "time_usage", "total_usage_volume", "volume", "total_cost"]

    def __init__(self, time_label):
        self.total_usage_volume = 0
        self.total_cost = Decimal(0)
        self.time_usage = 0
        self.min_time_label = self.max_time_label = time_label
        self.volume = None

    @property
    def start(self):
        return self.min_time_label.timestamp_range()[0]

    @property
    def finish(self):
        return self.max_time_label.timestamp_range()[1]


class ResourceUsageTime(ResourceUsageBase):
    def __init__(self, time_label):
        super().__init__(time_label)
        self.time_labels = {time_label.label}

    def add_usage(self, time_label, usage):
        if self.volume is not None:
            raise Exception("Add usage should be called only once")
        self.volume = usage.usage_volume

        self.time_labels.add(time_label.label)
        self.min_time_label = min(time_label, self.min_time_label)
        self.max_time_label = max(time_label, self.max_time_label)

        self.total_usage_volume += usage.usage_volume or 0
        self.total_cost += usage.cost
        self.time_usage += (usage.end - usage.start).total_seconds() + 1

    def merge(self, other):
        if self.volume != other.volume:
            return False

        assert not (self.time_labels & other.time_labels)
        self.time_labels.union(other.time_labels)
        self.total_cost += other.total_cost
        self.time_usage += other.time_usage
        self.total_usage_volume += other.total_usage_volume

        self.min_time_label = min(other.min_time_label, self.min_time_label)
        self.max_time_label = max(other.max_time_label, self.max_time_label)
        return True


class ResourceUsageQuantity(ResourceUsageBase):
    def __init__(self, time_label):
        super().__init__(time_label)
        self.time_usage = "-"

    # noinspection PyUnusedLocal
    def add_usage(self, time_label, usage):
        self.total_usage_volume += usage.usage_volume or 0
        self.total_cost += usage.cost or Decimal(0)


class ResourceReport(Serialized):
    json_fields = ["total_usage_volume", "total_cost", "intervals", "resource_name"]

    def __init__(self, resource_id, resource_name, service):
        self.resource_id = resource_id
        self.resource_name = resource_name
        self.time_labels = {}
        self.total_cost = Decimal(0)
        self.total_usage_volume = 0
        self.service = service

    def __str__(self):
        return "<ResourceReport %s %s %s cost: %s, volume: %s>" % (
            self.service.service_id, self.resource_id, self.resource_name, self.total_cost, self.total_usage_volume)

    def __repr__(self):
        return str(self)

    def add_usage(self, usage):
        time_label = TimeLabel.from_str(usage.time_label)
        current_data = self.time_labels.get(time_label.label)

        if current_data:
            logbook.error("At least two records for resource {} and time_label: {}. "
                          "Usages will be summarized. Usage: {}",
                          self.resource_id, time_label, usage)
            return

        measure_type = self.service.measure.measure_type if self.service else Measure.QUANTITATIVE
        quantitative_service = measure_type == Measure.QUANTITATIVE
        resource_usage_class = ResourceUsageQuantity if quantitative_service else ResourceUsageTime
        resource_usage = resource_usage_class(time_label)
        self.time_labels[time_label.label] = resource_usage
        resource_usage.add_usage(time_label, usage)
        if not quantitative_service:
            self.merge_with_neighbor(time_label, resource_usage)

        self.total_cost += usage.cost or Decimal(0)
        self.total_usage_volume += usage.usage_volume or 0

    @property
    def intervals(self):
        unique = set(self.time_labels.values())
        return sorted(unique, key=attrgetter("start"))

    def merge_with_neighbor(self, time_label, object_usage):
        previous_label = time_label.previous().label
        previous_usage = self.time_labels.get(previous_label)

        if previous_usage and previous_usage.merge(object_usage):
            self.time_labels[time_label.label] = previous_usage
            previous_merged = True
        else:
            previous_merged = False

        next_label = time_label.next().label
        next_usage = self.time_labels.get(next_label)
        if not next_usage:
            return

        if previous_merged:
            if previous_usage.merge(next_usage):
                self.time_labels[next_label] = previous_usage
                # previous + current + next are merged
                return

        if next_usage.merge(object_usage):
            self.time_labels[time_label.label] = next_usage


class DetailedServiceReport(SimpleServiceReport):
    json_fields = ["total_usage_volume", "price", "measure", "total_cost", "name", "category",
                   "service_id", "resources"]

    def __init__(self, service_id, customer, tariff):
        self.currency = tariff.currency
        self.service = Service.get_by_id(service_id)
        if self.service:
            self.name = self.service.get_localized_name(customer.locale_language())
            self.category = self.service.category.get_localized_name(customer.locale_language())
            self.measure = self.service.measure.get_localized_name(customer.locale_language())
            self.hours = self.service.hours
        else:
            self.name = str(service_id)
            self.category = ""
            self.measure = ""
            self.hours = 1

        self.price = tariff.service_price(service_id)
        self.service_id = service_id
        self.resources = {}

    def __str__(self):
        return "<usage: {0.total_usage_volume}, cost: {0.total_cost}, currency: {0.currency} " \
               "measure: {0.measure}".format(self)

    def __repr__(self):
        return str(self)

    def add_usage(self, service_usage):
        assert self.service_id == service_usage.service_id
        resource_id = service_usage.resource_id
        resource = self.resources.get(resource_id)
        if resource is None:
            resource = ResourceReport(resource_id, service_usage.resource_name, self.service)
            self.resources[resource_id] = resource
        resource.add_usage(service_usage)

    @cached_property
    def total_cost(self):
        total_cost = Decimal(0)
        for resource in self.resources.values():
            total_cost += resource.total_cost
        return total_cost

    @cached_property
    def total_usage_volume(self):
        volume = Decimal(0)
        for resource in self.resources.values():
            volume =+ resource.total_usage_volume
        return volume


class TariffReport(_TariffReport):
    def __init__(self, tariff, customer):
        super().__init__(tariff, customer)
        self._usage = {}

    def add_usage(self, usage):
        service_id = usage.service_id
        service_report = self._usage.get(service_id)
        if service_report is None:
            service_report = DetailedServiceReport(service_id, self.customer, self.tariff)
            self._usage[service_id] = service_report
        service_report.add_usage(usage)

    def aggregate(self):
        total_cost = Decimal(0)
        for service in self._usage.values():
            total_cost += service.total_cost

        self.total_cost = total_cost
        return self.total_cost, self.tariff.currency

    @property
    def usage(self):
        return list(self._usage.values())


class DetailedReport(CustomerReport):
    report_type = "detailed"
    tariff_report_type = TariffReport

    def aggregate(self, report_id):
        logbook.info("Get detailed customer usage aggregation for {}", report_id)

        customer = Customer.get_by_id(report_id.customer_id)
        if not customer:
            raise Exception("Customer %s not found" % report_id.customer_id)

        with timed("get_usage simple"):
            aggregated_usage = ServiceUsage.get_detailed_usage(customer, report_id.start, report_id.end)

        tariffs = {}
        services = set()
        for usage in aggregated_usage:
            tariff = Tariff.get_by_id(usage.tariff_id)
            tariff_report = tariffs.get(usage.tariff_id)
            if tariff_report is None:
                tariff_report = self.tariff_report_type(tariff, customer)
                tariffs[usage.tariff_id] = tariff_report

            tariff_report.add_usage(usage)

        total = Counter()
        for tariff_id, tariff in tariffs.items():
            total_tariff, currency = tariff.aggregate()
            total[currency] += total_tariff

        for t, value in total.items():
            total[t] = decimal_to_string(value)

        logbook.info("Aggregated {} for {}. Services: {}", total, customer, services)
        return self.prepare_result(list(tariffs.values()), total, customer, report_id.start, report_id.end)
