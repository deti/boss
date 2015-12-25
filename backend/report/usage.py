import logbook
from report import Report
from model import ServiceUsage


class UsageReport(Report):
    report_type = "usage"

    def aggregate(self, report_id):
        logbook.info("Get usage aggregation for {}", report_id)

        usage_by_customer = ServiceUsage.customers_get_usage(report_id.start, report_id.end)
        result = []
        for customer, usages in usage_by_customer.items():
            for usage in usages:
                currency, withdraw = usage
                d = {"email": customer.email,
                     "withdraw": withdraw,
                     "currency": currency,
                     }
                result.append(d)
        return result


class OpenstackUsageReport(Report):
    report_type = "openstack_usage"
    cache_time = 30
    report_cache_time = 30

    def aggregate(self, report_id):
        from memdb.report_cache import ReportCache

        # get data stat cache
        locale_less_report_id = report_id.replace(locale=None)
        data = ReportCache().get_report_aggregated(locale_less_report_id)
        return data
