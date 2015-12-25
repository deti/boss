import errors
import json
import logbook
import bottle
from model import autocommit, display, Customer
from api import get, post, AdminApi
from api.check_params import check_params
from api.admin.role import TokenManager
from api.cabinet.customer import DateHourBeforeNow
from memdb.report_cache import ReportCache, ReportId, ReportTask
from report import Report
from utils import make_content_disposition
from task.customer import report_file_generate
from datetime import timedelta
from api.validator import ActiveLocale, Choose, Bool
from statistics import IPsStats


class ReportApi(AdminApi):
    @post("report/receipts/")
    @check_params(
        token=TokenManager,
        start=DateHourBeforeNow(),
        finish=DateHourBeforeNow(timedelta(hours=2)),
        locale=ActiveLocale(),
        report_format=Choose(["csv", "tsv"])
    )
    @autocommit
    def receipts(self, start, finish, locale="ru_ru", report_format="csv"):
        """
        Asynchronous create an report that lists all receipts of funds for all customers

        :param DateHour start: Start report period
        :param DateHour finish: End report period
        :param Locale locale: Locale for the report
        :param Str report_format: report format. Currently supported the following formats: csv, tsv

        This method returns report as is (content type is set depend on report format) when report is ready, or returns
        status of report task generation.

        **Example**::


            {
                "status": "in progress",
            }

        """

        return self.report(start, finish, "receipts", report_format, locale)

    @post("report/usage/")
    @check_params(
        token=TokenManager,
        start=DateHourBeforeNow(),
        finish=DateHourBeforeNow(timedelta(hours=2)),
        locale=ActiveLocale(),
        report_format=Choose(["csv", "tsv"])
    )
    @autocommit
    def usage(self, start, finish, locale="ru_ru", report_format="csv"):
        """
        Asynchronous create an report that lists used resources for all customers

        :param DateHour start: Start report period
        :param DateHour finish: End report period
        :param Locale locale: Locale for the report
        :param Str report_format: report format. Currently supported the following formats: csv, tsv

        This method returns report as is (content type is set depend on report format) when report is ready, or returns
        status of report task generation.

        **Example**::

            {
                "status": "in progress",
            }

        """

        return self.report(start, finish, "usage", report_format, locale)

    def report(self, start, finish, report_type, report_format, locale=None):
        if start >= finish:
            raise errors.StartShouldBeEarlierFinish()

        if not Report.is_supported(report_type, report_format):
            raise errors.ReportFormatIsNotSupported()

        report_cache = ReportCache()
        report_task = ReportTask()
        report_id = ReportId(start, finish, report_type, report_format, locale)

        data = report_cache.get_report(report_id)

        if data:
            if report_format == "json":
                return {"status": "completed",
                        "report": json.loads(data.decode("utf-8"))}
            filename = Report.generate_file_name(report_type, start, finish, report_format)
            content_disposition = make_content_disposition(filename, bottle.request.environ.get('HTTP_USER_AGENT'))
            return bottle.HTTPResponse(body=data, content_type=Report.content_types[report_format],
                                       content_disposition=content_disposition)

        status = report_task.task_status(report_id)
        if not status:
            result = report_file_generate.delay(report_id)
            logbook.info("Created report_file task {} for {}", result.id, report_id)
            report_task.set(report_id, result.id)
            status = "started"
        return {"status": status}

    @get("stat/ips/")
    @check_params(token=TokenManager)
    @autocommit
    def statistics(self):
        """Returns IP address statistics.

        **Example**::

        {
            "floating_ips": {
                 'active_customer': 4,
                 'blocked_customer': 1,
                 'customer_mode-production': 1,
                 'customer_mode-test': 4,
                 'customer_type-entity': 1,
                 'customer_type-private': 4,
                 'ip_status-DOWN': 3,
                 'ip_status-UP': 2,
                 'total': 5
            }
        }

        """
        ips_stat = IPsStats().stat()
        return {"floating_ips": ips_stat}

    @post("stat/customer/")
    @check_params(
        token=TokenManager
    )
    @autocommit
    def customers_stats(self):
        """
        Returns customer statistics.

        **Example**::

            {
              "customer_stats": {
                "pending_prod_private": 0,
                "production": 2,
                "pending_prod_private_blocked": 0,
                "pending_prod": 0,
                "total": 5,
                "private_deleted": 1,
                "production_private_blocked": 0,
                "entity_deleted": 0,
                "total_test": 3,
                "pending_prod_entity_blocked": 0,
                "production_private": 2,
                "test_private_blocked": 1,
                "production_entity_blocked": 0,
                "test_entity_blocked": 0,
                "production_entity": 0,
                "test_private": 2,
                "test_entity": 1,
                "pending_prod_entity": 0,
                "total_blocked": 1,
                "total_deleted": 1
              }
            }

        """

        return {"customer_stats": Customer.customers_stat()}

    @post("stat/openstack/usage/")
    @check_params(
        token=TokenManager,
        force=Bool,
        locale=ActiveLocale(),
        report_format=Choose(["csv", "tsv", "json"])
    )
    @autocommit
    def openstack_usage(self, locale="ru_ru", report_format="json", force=False):
        """
        Asynchronous create an report that lists used resources by each customer. The data is provided by open stack

        :param Locale locale: Locale for the report.
        :param bool force: Force to retrieve latest data.
        :param Str report_format: report format. Currently supported the following formats: csv, tsv, json

        This method returns report as is (content type is set depend on report format) when report is ready, or returns
        status of report task generation.

        **Example**::

            {
                "status": "in progress",
            }

        """

        return self.current_stat("openstack_usage", report_format, locale, force)

    @staticmethod
    def current_stat(report_type, report_format, locale=None, force=False):
        if not Report.is_supported(report_type, report_format):
            raise errors.ReportFormatIsNotSupported()

        report_cache = ReportCache()
        report_task = ReportTask()
        report_id = ReportId(None, None, report_type, report_format, locale)

        if not force:
            data = report_cache.get_report(report_id)
            if data:
                if report_format == "json":
                    return {"status": "completed",
                            "report": json.loads(data.decode("utf-8"))}
                filename = "%s.%s" % (report_type, report_format)
                content_disposition = make_content_disposition(filename, bottle.request.environ.get('HTTP_USER_AGENT'))
                return bottle.HTTPResponse(body=data, content_type=Report.content_types[report_format],
                                           content_disposition=content_disposition)

        status = report_task.task_status(report_id)
        if not status:
            result = report_file_generate.delay(report_id)
            logbook.info("Created report_file task {} for {}", result.id, report_id)
            report_task.set(report_id, result.id)
            status = "started"
        return {"status": status}

