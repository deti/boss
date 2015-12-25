import logbook
from decimal import Decimal
from model import Service, Customer, ServiceUsage, Tariff
from report import CustomerReport, Serialized
from collections import Counter
from utils import timed
from utils.money import decimal_to_string


class ServiceReport(Serialized):
    json_fields = ["total_usage_volume", "price", "measure", "total_cost", "name", "category",
                   "service_id"]

    def __init__(self, service_usage, customer, tariff):
        self.currency = tariff.currency
        service_id, tariff_id, total_cost, total_usage_volume = service_usage
        service = Service.get_by_id(service_id)
        if service:
            self.name = service.get_localized_name(customer.locale_language())
            self.category = service.category.get_localized_name(customer.locale_language())
            self.measure = service.measure.get_localized_name(customer.locale_language())
            self.hours = service.hours
        else:
            self.name = str(service_id)
            self.category = ""
            self.measure = ""
            self.hours = 1

        self.total_cost = total_cost or Decimal(0)
        self.total_usage_volume = total_usage_volume or 0
        self.price = tariff.service_price(service_id) or Decimal(0)
        self.service_id = service_id

    def __str__(self):
        return "<usage: {0.total_usage_volume}, cost: {0.total_cost}, currency: {0.currency} " \
               "measure: {0.measure}".format(self)


class TariffReport(Serialized):
    json_fields = ["total_cost", "currency", "usage", "name"]

    def __init__(self, tariff, customer):
        self.tariff = tariff
        self.customer = customer
        self.total_cost = None
        self._usage = []

    def add_usage(self, usage):
        self._usage.append(ServiceReport(usage, self.customer, self.tariff))

    def aggregate(self):
        total_cost = Decimal(0)
        for service in self.usage:
            total_cost += service.total_cost or Decimal(0)

        self.total_cost = total_cost
        return self.total_cost, self.tariff.currency

    @property
    def currency(self):
        return self.tariff.currency

    @property
    def name(self):
        return self.tariff.get_localized_name(self.customer.locale_language)

    @property
    def usage(self):
        return self._usage


class SimpleReport(CustomerReport):
    report_type = "simple"
    tariff_report_type = TariffReport

    def aggregate(self, report_id):
        logbook.info("Get customer usage aggregation for {}", report_id)
        customer = Customer.get_by_id(report_id.customer_id)
        if not customer:
            raise Exception("Customer %s not found" % report_id.customer_id)

        with timed("get_usage simple"):
            aggregated_usage = ServiceUsage.get_usage(customer, report_id.start, report_id.end)

        tariffs = {}
        services = set()
        for usage in aggregated_usage:
            service_id, tariff_id, cost, usage_volume = usage
            services.add(service_id)
            if not tariff_id:
                logbook.error("ServiceUsage {} is not completed. Tariff is not filled", usage)
                continue
            tariff = Tariff.get_by_id(tariff_id)
            tariff_report = tariffs.get(tariff_id)
            if tariff_report is None:
                tariff_report = self.tariff_report_type(tariff, customer)
                tariffs[tariff_id] = tariff_report

            tariff_report.add_usage(usage)

        total = Counter()
        for tariff_id, tariff in tariffs.items():
            total_tariff, currency = tariff.aggregate()
            total[currency] += total_tariff

        for t, value in total.items():
            total[t] = decimal_to_string(value)

        logbook.info("Aggregated {} for {}. Services: {}", total, customer, services)
        return self.prepare_result(list(tariffs.values()), total, customer, report_id.start, report_id.end)


class AcceptanceActReport(SimpleReport):
    report_type = "acceptance_act"
