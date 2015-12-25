# -*- coding: utf-8 -*-
import conf
from task.main import celery, exception_safe_task
from task.mail import send_email
from model import Customer, MessageTemplate, db
from os_interfaces.openstack_wrapper import openstack
import logbook as log


def send_email_os_credentials(email, name, password, tenant_id, language):
    subject, body = MessageTemplate.get_rendered_message(MessageTemplate.OS_CREDENTIALS,
                                                         language=language,
                                                         os_name=name, os_password=password,
                                                         os_tenant=tenant_id, os_region=conf.openstack.region,
                                                         os_horizon_url=conf.openstack.horizon_url,
                                                         os_keystone_url=conf.openstack.customer_keystone_url)

    log.debug("Sending email with OpenStack credentials to {}", name)
    send_email.delay(email, subject, body)


@celery.task(ignore_result=True, max_retries=conf.openstack.max_retries,
             default_retry_delay=conf.openstack.retry_delay, rate_limit=conf.openstack.rate_limit)
@exception_safe_task()
def task_os_create_tenant_and_user(customer_id, email):
    # email is just for logs
    customer = Customer.get_by_id(customer_id)
    log.debug("task_os_create_tenant_and_user: {}", customer)
    if not customer:
        log.warning("Can't find customer {} {}. Possible customer was removed by system test", customer_id, email)
        return

    info = openstack.create_tenant_and_user(email, customer_id, customer.tariff.flavors(),
                                            password=customer.os_user_password, enabled=True)
    log.debug("Openstack info: {}", info)

    # Tests can delete customer already here, therefore no updates are required
    if not conf.test:
        db.session.commit()
        db.session.close()
    customer = Customer.get_by_id(customer_id)
    if customer:
        customer.update_os_credentials(info['tenant_id'], info['tenant_name'],
                                       info['user_id'], info["username"], info['password'])
        send_email_os_credentials(info['email'], info['name'], info['password'], info['tenant_id'],
                                  language=customer.locale_language())
        db.session.commit()
    else:
        final_delete_from_os(info['tenant_id'], info['user_id'])


@celery.task(ignore_result=True, max_retries=conf.openstack.max_retries,
             default_retry_delay=conf.openstack.retry_delay, rate_limit=conf.openstack.rate_limit)
@exception_safe_task()
def reset_user_password(customer_id):
    customer = Customer.get_by_id(customer_id)

    if not customer:
        log.warning("Can't find customer for reset user password {} {}. Possible customer was removed by system test",
                    customer_id)
        return

    password = openstack.reset_user_password(customer.os_user_id)
    customer.update_os_password(password)
    send_email_os_credentials(customer.email, customer.os_username, password, customer.os_tenant_id,
                              language=customer.locale_language())


@celery.task(ignore_result=True, max_retries=conf.openstack.max_retries,
             default_retry_delay=conf.openstack.retry_delay, rate_limit=conf.openstack.rate_limit)
@exception_safe_task(new_session=False, auto_commit=False)
def stop_instances(tenant_id):
    log.info("Stopping instances of tenant {}", tenant_id)
    openstack.stop_instances(tenant_id)


@celery.task(ignore_result=True, max_retries=conf.openstack.max_retries,
             default_retry_delay=conf.openstack.retry_delay, rate_limit=conf.openstack.rate_limit)
@exception_safe_task(new_session=False, auto_commit=False)
def delete_floating_ips(tenant_id):
    log.info("Deleting floating ips of tenant {}", tenant_id)
    openstack.delete_floating_ips(tenant_id)


@celery.task(ignore_result=True, max_retries=conf.openstack.max_retries,
             default_retry_delay=conf.openstack.retry_delay, rate_limit=conf.openstack.rate_limit)
@exception_safe_task(new_session=False, auto_commit=False)
def block_user(user_id, blocked):
    log.info("{} user {} in openstack", 'Blocking' if blocked else 'Unblocking', user_id)
    openstack.update_user(user_id, enabled=not blocked)


@celery.task(ignore_result=True, max_retries=conf.openstack.max_retries,
             default_retry_delay=conf.openstack.retry_delay, rate_limit=conf.openstack.rate_limit)
@exception_safe_task(new_session=False, auto_commit=False)
def final_delete_from_os(tenant_id, user_id):
    log.info("Final deleting user {} with tenant {} from openstack", user_id, tenant_id)
    openstack.final_delete(user_id, tenant_id)


@celery.task(ignore_result=True, max_retries=conf.openstack.max_retries,
             default_retry_delay=conf.openstack.retry_delay, rate_limit=conf.openstack.rate_limit)
@exception_safe_task(new_session=False, auto_commit=False)
def delete_only_resources(tenant_id):
    log.info("Deleting resources of tenant {} from openstack", tenant_id)
    openstack.delete_resources(tenant_id)


@celery.task(ignore_result=True, max_retries=conf.openstack.max_retries,
             default_retry_delay=conf.openstack.retry_delay, rate_limit=conf.openstack.rate_limit)
@exception_safe_task(new_session=False, auto_commit=False)
def create_flavor(name, vcpus, ram, disk, is_public=True):
    log.info("Creating flavor {} ", name)
    openstack.create_flavor(name, ram, vcpus, disk, is_public=is_public)


@celery.task(ignore_result=True, max_retries=conf.openstack.max_retries,
             default_retry_delay=conf.openstack.retry_delay, rate_limit=conf.openstack.rate_limit)
@exception_safe_task(new_session=False, auto_commit=False)
def delete_flavor(name):
    log.info("Deleting flavor {}", name)
    openstack.delete_flavor(name)

