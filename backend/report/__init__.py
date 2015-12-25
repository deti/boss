# -*- coding: utf-8 -*-
import conf
import re
from report.formatter import LocaleFormatter
from report.render import Render
from model import Service
from arrow import utcnow


class Serialized(object):

    json_fields = []

    def to_json(self):
        result = {}
        for f in self.json_fields:
            result[f] = getattr(self, f)
        return result

    def __str__(self):
        return self.__class__.__name__ + str(self.to_json())

    def __getitem__(self, key):
        return self.__getattribute__(key)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default


class Report:
    report_types = {}
    report_type = None
    _os_invalid_file_name_characters = r'[]/\;,><&*:%=+@!#^()|?^"'
    _os_invalid_file_name_characters_pattern = "|".join(re.escape(q) for q in _os_invalid_file_name_characters)
    cache_time = None
    report_cache_time = None

    content_types = {"pdf": "application/pdf",
                     "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                     "json": "application/json",
                     "csv": "text/csv",
                     "tsv": "text/csv"}

    def __init__(self):
        self.services = {}

    @classmethod
    def register_type(cls):
        cls.report_types[cls.report_type] = cls

    @classmethod
    def supported_formats(cls, report_type):
        return list(conf.report.configuration[report_type].keys())

    @classmethod
    def supported_formats(cls, report_type):
        return list(conf.report.configuration[report_type].keys())

    @classmethod
    def is_supported(cls, report_type, report_format):
        if report_format == "tsv":
            report_format = "csv"
        return report_format in cls.supported_formats(report_type)

    @classmethod
    def get_report(cls, report_type):
        return cls.report_types[report_type]()

    def render(self, aggregated, report_id):
        r = Render.get_render(report_id.report_format)
        f = LocaleFormatter(report_id.locale)
        return r.render(aggregated, self.report_type, report_id.locale, money=f.money)

    @staticmethod
    def generate_file_name(customer_name, start, end, report_format, locale=None):
        customer_name = customer_name or ""
        start = start.strftime("%Y-%m-%d")
        name_parts = [customer_name, start]
        if end:
            end = end.strftime("%Y-%m-%d")
            name_parts.append(end)
        if locale:
            name_parts.append(locale)
        name = "_".join(name_parts)
        if report_format == "tsv":
            report_format = "csv"
        name += "." + report_format
        return re.sub(Report._os_invalid_file_name_characters_pattern, '_', name)

    def aggregate(self, report_id):
        pass

    def get_service(self, service_id):
        service = self.services.get(service_id)
        if not service:
            service = Service.get_by_id(service_id)
            if not service:
                raise ValueError("Service %s not found" % service_id)
        return service


class CustomerReport(Report):
    tariff_report_type = None
    _os_invalid_file_name_characters = r'[]/\;,><&*:%=+@!#^()|?^"'
    _os_invalid_file_name_characters_pattern = "|".join(re.escape(q) for q in _os_invalid_file_name_characters)


    @staticmethod
    def prepare_result(aggregated, total, customer, start, finish):
        result = {
            "report_range": {"start": start, "finish": finish},
            "tariffs": aggregated,
            "total": total,
            "customer": customer.report_info(),
            "report_date": utcnow().datetime
        }
        return result


from report.simple import SimpleReport, AcceptanceActReport
from report.detailed import DetailedReport
from report.receipts import ReceiptsReport
from report.usage import UsageReport, OpenstackUsageReport

SimpleReport.register_type()
DetailedReport.register_type()
ReceiptsReport.register_type()
UsageReport.register_type()
AcceptanceActReport.register_type()
OpenstackUsageReport.register_type()
