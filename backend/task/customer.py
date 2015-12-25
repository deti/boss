import conf
import logbook
from pytz import utc
from arrow import utcnow
from memdb.report_cache import ReportCache, CustomerReportId
from report import Report
from task.main import celery, exception_safe_task
from model import db, Deferred, MessageTemplate
from utils import day_start, timed
from decimal import Decimal
from os_interfaces.openstack_wrapper import openstack


@celery.task()
def process_pending_deferred_customer_changes(time_now=None, name_prefix=None):
    return Deferred.process_pending_deferred_changes(time_now, name_prefix)


def get_aggregation(report_id):
    from report import Report

    report_generator = Report.get_report(report_id.report_type)

    aggregated = report_generator.aggregate(report_id)
    report_cache = ReportCache()
    report_cache.set_report_aggregated(report_id, aggregated, report_generator.cache_time)
    return aggregated


@celery.task(bind=True,
             max_retries=conf.report.max_retries,
             default_retry_delay=conf.report.retry_delay)
@exception_safe_task()
def report_file_generate(self, report_id):
    from report import Report
    from memdb.report_cache import ReportCache, ReportTask

    report_cache = ReportCache()

    aggregated = report_cache.get_report_aggregated(report_id)
    if not aggregated:
        aggregated = get_aggregation(report_id)
        aggregated = ReportCache.unpack_aggregated(ReportCache.pack_aggregated(aggregated))
    report_generator = Report.get_report(report_id.report_type)
    with timed("rendering for %s" % report_id):
        data = report_generator.render(aggregated, report_id)
    report_cache.set_report(report_id, data, report_generator.report_cache_time)
    ReportTask().remove(report_id)


@celery.task(max_retries=conf.report.max_retries,
             default_retry_delay=conf.report.retry_delay,
             ignore_result=True,
             bind=True)
@exception_safe_task(new_session=not conf.test)
def clean_up_customer_service_usage(self, customer_id, end_date):
    from model import Customer
    customer = Customer.get_by_id(customer_id)
    if not customer:
        logbook.warning("Customer id '{}' not found for cleaning up services usage", customer_id)
        return
    customer.clean_up_service_usage(end_date)


@celery.task(ignore_result=True)
@exception_safe_task()
def auto_report(time_now=None, email_prefix=None):
    from model import Customer
    if time_now is None:
        time_now = utcnow().datetime

    tasks = Customer.auto_withdraw_query(email_prefix, now=time_now).all()
    logbook.info("Found {} task for auto report", len(tasks))

    for task in tasks:
        customer_auto_report.delay(task.customer_id, time_now)

    return len(tasks)


@celery.task(ignore_result=True)
@exception_safe_task()
def customer_auto_report(customer_id, time_now):
    from model import Customer, ScheduledTask
    from task.mail import send_email
    customer = Customer.get_by_id(customer_id)

    if not customer:
        logbook.error("Can't find customer {} for report generation", customer_id)
        return

    report_task = ScheduledTask.get_by_customer(customer_id, Customer.AUTO_REPORT_TASK)
    if not report_task:
        logbook.error("Can't find auto report task for customer {}", customer_id)
        return

    logbook.debug("Start auto-report task for customer {}: {}", customer, report_task)

    report_task.start()

    previous_next_send = report_task.next_scheduled.replace(tzinfo=utc)
    if previous_next_send is None or previous_next_send > time_now:
        logbook.warning("Looks like report for customer {} already sent. Next send: {}, current time {}",
                        customer, previous_next_send, time_now)
        report_task.completed(now=time_now)
        return

    report_begin = day_start(report_task.last or time_now)
    _, report_end = report_task.task_range(time_now, previous_interval=True)
    report_end = day_start(report_end)

    report_id = CustomerReportId(customer.customer_id, report_begin, report_end,
                                 conf.customer.report.type, conf.customer.report.format, customer.locale)
    report_file_generate(report_id)

    # report_file_generate closed session so we should initialize customer again
    customer = Customer.get_by_id(customer_id)
    report_task = ScheduledTask.get_by_customer(customer_id, Customer.AUTO_REPORT_TASK)

    report_cache = ReportCache()

    report = report_cache.get_report_aggregated(report_id)

    if not report or not report["tariffs"]:
        logbook.info("Report is empty for customer {}", customer)
        report_task.completed(now=time_now)
        return

    report_file = report_cache.get_report(report_id)

    if not report_file:
        logbook.error("Report generation failed")
        report_task.completed(False)
        return

    filename = Report.generate_file_name(customer.get_name(), report_begin, report_end, conf.customer.report.format)

    subject, body = MessageTemplate.get_rendered_message(
        MessageTemplate.CUSTOMER_AUTO_REPORT, customer.locale_language(),
        customer_name=customer.get_name(), currency=customer.tariff.currency,
        report_start=report_begin, report_end=report_end)


    subscription_info = customer.subscription_info()['billing']

    if subscription_info["enable"]:
        send_email.delay(subscription_info["email"], subject, body, attachments=[(filename, report_file)])

    report_task.completed(now=time_now)
    comment_fmt = "%s - %s" % (report_begin.strftime('%Y-%m-%d'), report_end.strftime('%Y-%m-%d'))

    for currency, amount in report["total"].items():
        amount = Decimal(amount)
        customer.modify_balance(-amount, currency, None, comment_fmt)
        account = customer.get_account(currency)
        account.charge(-amount)

    db.session.commit()


@celery.task(ignore_result=True)
@exception_safe_task()
def time_state_check():
    from model import TimeMachine

    TimeMachine.check()


@celery.task(ignore_result=True)
@exception_safe_task()
def get_used_quotas(customer_id):
    from model import Customer
    customer = Customer.get_by_id(customer_id)
    if not customer:
        logbook.warning("Customer id '{}' not found for getting used quotas", customer_id)
        return
    customer.get_used_quotas()


@celery.task(ignore_result=True)
@exception_safe_task(new_session=False)
def change_flavors(tenant_id, flavors):
    openstack.change_flavors(tenant_id, flavors)


@celery.task(ignore_result=True)
@exception_safe_task()
def update_quota(customer_id, user_id, quotas):
    from model import Customer, CustomerHistory

    customer = Customer.get_by_id(customer_id)
    if not customer:
        logbook.warning("Customer id '{}' not found for quota update", customer_id)
        return

    customer = Customer.get_by_id(customer_id)
    openstack.change_tenant_quotas(customer.os_tenant_id, **quotas)
    CustomerHistory.quota_changed(customer, user_id, None)

