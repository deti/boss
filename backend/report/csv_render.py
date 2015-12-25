from collections import namedtuple
from io import StringIO
import codecs
import csv
import re

from report import Render
from report import LocaleFormatter
from utils.money import string_to_decimal, decimal_to_string


class CSVRender(Render):
    output_format = "csv"
    money_pattern = re.compile(r"\d+\.\d\d")

    def __init__(self, template_dir=None):
        super().__init__(template_dir)
        self.writer = None

    @staticmethod
    def linear(aggregated):
        for tariff in aggregated["tariffs"]:
            for usage in tariff["usage"]:
                usage = usage.copy()
                usage["tariff_name"] = tariff["name"]
                usage["tariff_currency"] = tariff["currency"]
                yield usage

    def format_money(self, money, locale):
        if isinstance(money, str) and self.money_pattern.match(money):
            money = decimal_to_string(string_to_decimal(money), locale=locale)

        return money

    def encode(self, csvfile, locale):
        encoding = "cp1251" if locale and locale.startswith("ru") else "ascii"
        return csvfile.getvalue().encode(encoding)

    def _render(self, aggregated, configuration, locale, language, **kwargs):
        render = configuration["render"]
        render_method = getattr(self, render)
        rendered = render_method(aggregated, configuration, locale, language, **kwargs)
        return self.encode(rendered, locale)

    def get_writer(self, csvfile, locale):
        delimiter = ";" if locale.startswith("ru") else ","
        return csv.writer(csvfile, delimiter=delimiter)

    def detailed(self, aggregated, configuration, locale, language, **kwargs):
        formatter = LocaleFormatter(locale)

        csvfile = StringIO()
        customer = aggregated["customer"]
        report_range = aggregated["report_range"]
        self.writer = self.get_writer(csvfile, locale)

        self.writer.writerow(("Customer name", "Start", "Finish"))
        self.writer.writerow((customer["name"] or customer["email"],
                              formatter.datetime(report_range["start"]),
                              formatter.datetime(report_range["finish"])))
        self.writer.writerow([])

        headers = configuration['headers']

        Service = namedtuple('Service', 'service_category '
                                        'resource_name '
                                        'service_name '
                                        'service_measure '
                                        'service_price '
                                        'interval_start '
                                        'interval_finish '
                                        'interval_time_usage '
                                        'interval_volume '
                                        'interval_total_cost')

        if aggregated.get('tariffs'):
            for tariff in aggregated['tariffs']:
                self.writer.writerow([])
                self.writer.writerow(('Tariff', 'Tariff currency'))
                self.writer.writerow((tariff['name'], tariff['currency']))

                self.writer.writerow(list(headers.values()))
                for service in tariff['usage']:
                    for resource_id, resource_data in service['resources'].items():
                        for interval in resource_data['intervals']:
                            s = Service(service['category'],
                                        resource_data["resource_name"] or resource_id,
                                        service['name'],
                                        service['measure'],
                                        self.format_money(service['price'] or "0", locale),
                                        formatter.datetime(interval['start']),
                                        formatter.datetime(interval['finish']),
                                        interval['time_usage'],
                                        interval['volume'],
                                        self.format_money(interval['total_cost'], locale))
                            row = [getattr(s, h) for h in headers]
                            self.writer.writerow(row)
                self.writer.writerow(("Tariff total: ", tariff['total_cost']))
        return csvfile

    def simple(self, aggregated, configuration, locale, language, **kwargs):
        formatter = LocaleFormatter(locale)

        csvfile = StringIO()
        customer = aggregated["customer"]
        report_range = aggregated["report_range"]
        self.writer = self.get_writer(csvfile, locale)
        self.writer.writerow(("Customer name", customer["name"] or customer["email"]))
        self.writer.writerow(("Start: ", formatter.datetime(report_range["start"])))
        self.writer.writerow(("Finish: ", formatter.datetime(report_range["finish"])))
        self.writer.writerow([])

        header = configuration["headers"]
        self.writer.writerow(list(header.values()))
        for usage in self.linear(aggregated):
            self.writer.writerow([self.format_money(usage[h], locale) for h in header])

        return csvfile

    def receipts(self, aggregated, configuration, locale, language, **kwargs):
        csvfile = StringIO()
        self.writer = self.get_writer(csvfile, locale)

        header = configuration["headers"]
        self.writer.writerow(list(header.values()))
        for row in aggregated:
            self.writer.writerow([row[h] for h in header])

        return csvfile

    def usage(self, aggregated, configuration, locale, language, **kwargs):
        csvfile = StringIO()
        self.writer = self.get_writer(csvfile, locale)

        header = configuration["headers"]
        self.writer.writerow(list(header.values()))
        for row in aggregated:
            self.writer.writerow([row[h] for h in header])

        return csvfile


class TSVRender(CSVRender):
    output_format = "tsv"

    def get_writer(self, csvfile, locale):
        return csv.writer(csvfile, dialect='excel-tab')

    def encode(self, csvfile, locale):
        return codecs.BOM_UTF16_LE + csvfile.getvalue().encode("utf-16le")

    def config_format(self):
        return "csv"
