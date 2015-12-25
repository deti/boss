import arrow
import conf
import logbook
import datetime
import posixpath
from api import request_base_url
from task.main import celery, exception_safe_task
from task.mail import send_email
from model import Customer, MessageTemplate
from utils.i18n import preferred_language
from urllib.parse import urljoin


def send_email_limit_notification(email, days, language):
    block_date = arrow.utcnow() + datetime.timedelta(days=days)
    subject, body = MessageTemplate.get_rendered_message(MessageTemplate.CUSTOMER_BALANCE_LIMIT,
                                                         language=language,
                                                         block_date=block_date.datetime)
    logbook.info("Sending email with balance limit notification to {}", email)
    send_email.delay(email, subject, body)


def check_account_balance_limit(customer):
    today = arrow.utcnow()
    yesterday = today - datetime.timedelta(hours=24)

    from model import ServiceUsage
    day_withdraw = ServiceUsage.get_withdraw(customer, start=yesterday.datetime, finish=today.datetime)

    # Check we found any withdraws
    if not day_withdraw.get(customer.tariff.currency):
        return False, 0

    account = customer.get_account(customer.tariff.currency)
    lifetime = (account.current - customer.balance_limit) / (day_withdraw[customer.tariff.currency])
    logbook.debug("[check_account_balance_limit] customer: {} balance:{}, current:{}, lifetime:{}.",
                  customer, account.balance, account.current, lifetime)

    if lifetime <= conf.customer.blocking.notification:
        return True, lifetime
    return False, 0


@celery.task(bind=True, ignore_result=True)
@exception_safe_task(auto_commit=False)
def check_customers_for_balance(self, time_now=None, name_prefix=None):
    logbook.info("Celery task: check customers for balance.")
    for customer in Customer.query.filter_by(blocked=False):
        is_send, lifetime = check_account_balance_limit(customer)
        if is_send:
            send_email_limit_notification(customer.email, int(lifetime), customer.locale_language())


def send_email_hdd_notification(manager_email, block_date, account):
    subject, body = MessageTemplate.get_rendered_message(MessageTemplate.CUSTOMER_HDD_DELETE,
                                                         language=preferred_language(),
                                                         block_date=block_date,
                                                         account=account)

    logbook.info("Sending email notification to delete data of {}", account)
    send_email.delay(manager_email, subject, body)


def get_customers_manager(customer):
    return conf.customer.manager.email


@celery.task(bind=True, ignore_result=True)
@exception_safe_task(auto_commit=False)
def notify_managers_about_hdd(self, customer_id):
    customer = Customer.get_by_id(customer_id)
    if not customer:
        logbook.error("Customer {} not found in notify manager", customer_id)
        return
    logbook.info("notify manager about hdd for removing for customer {}", customer)
    from model.account.customer_history import CustomerHistory
    block_event = CustomerHistory.get_last_block_event(customer)
    send_email_hdd_notification(get_customers_manager(customer),
                                block_event.date,
                                customer.email)


@celery.task(bind=True, ignore_result=True)
@exception_safe_task(auto_commit=False)
def notify_managers_about_new_service_in_tariff(self, customer_id, flavor_name):
    customer = Customer.get_by_id(customer_id)
    if not customer:
        logbook.error("Customer {} not found in notify manager", customer_id)
        return
    logbook.info("notify manager about adding new service to tariff {}", customer.tariff.name)
    from api.admin.user import UserApi
    service_edit_url = urljoin(request_base_url(), posixpath.join(UserApi.ADMIN_FRONTEND_PATH, "tariffs",
                                                                  str(customer.tariff.tariff_id), "services"))
    customer_url = urljoin(request_base_url(), posixpath.join(UserApi.ADMIN_FRONTEND_PATH, "index",
                                                              str(customer.customer_id), "info"))

    subject, body = MessageTemplate.get_rendered_message(MessageTemplate.NEW_SERVICE_IN_TARIFF,
                                                         language=preferred_language(),
                                                         account=customer.email,
                                                         flavor_name=flavor_name,
                                                         tariff=customer.tariff.name,
                                                         customer_url=customer_url,
                                                         service_edit_url=service_edit_url)

    logbook.info("Sending email notification to delete data of {}", customer.email)
    send_email.delay(get_customers_manager(customer), subject, body)


@celery.task(ignore_result=True)
@exception_safe_task()
def hour_stats():
    from statistics import all_stats
    for stat_name in all_stats:
        hour_stats_individual.delay(stat_name)


@celery.task(bind=True, ignore_result=True, default_retry_delay=2, max_retries=5)
@exception_safe_task()
def hour_stats_individual(self, stat_name):
    from statistics import all_stats
    stat = all_stats[stat_name]
    stat.tick()
