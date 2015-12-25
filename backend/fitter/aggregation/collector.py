from operator import attrgetter
import conf
import logbook
from datetime import datetime, timedelta
from fitter.aggregation.timelabel import TimeLabel
from fitter.aggregation.transformers import get_transformer
from model.fitter.service_usage import ServiceUsage
from utils import handle_exception, timed
from model import db, Tenant, Customer
from utils.periodic_task import PeriodicTask
from collections import defaultdict
from fitter.aggregation.constants import date_format, other_date_format
from os_interfaces import openstack_wrapper
from memdb.mutex import RedisMutex
from memdb import MemDbModel
from sqlalchemy.orm.exc import ObjectDeletedError


class TenantMutex(RedisMutex):
    prefix = "tenant_mutex:"

    def __init__(self, tenant, ttl_ms=None):
        name = "tenant_%s" % tenant.tenant_id
        super().__init__(name, MemDbModel.redis, ttl_ms=ttl_ms or conf.fitter.tenant_mutex_ttl * 1000)


class Collector(PeriodicTask):
    def __init__(self):
        super().__init__(conf.fitter.fetch_interval)
        self.errors = 0
        self.window_leading = timedelta(seconds=conf.fitter.window_leading)
        self.dawn_of_time = conf.fitter.dawn_of_time

    def task(self):
        res = self.run_usage_collection()
        logbook.debug("usage: {}", res)
        db.session.remove()

    @handle_exception()
    def run_usage_collection(self, end=None):
        # Run usage collection on all tenants present in Keystone.
        db.session.close()
        tenants = Tenant.all_active_tenants()

        usage = {}
        for tenant in tenants:
            try:
                tenant_id = tenant.tenant_id  # session can be closed during next call, so we should cache tenant_id
            except ObjectDeletedError as e:
                logbook.warning("Tenant {} was removed from db (probably during cleanup after test: ", tenant_id, e)

            next_run_delay = None
            with TenantMutex(tenant) as mutex:
                if mutex:
                    logbook.debug("Processing tenant: {}", tenant_id)
                    tenant_usage = self.collect_usage(tenant, mutex, end)
                    usage[tenant_id] = tenant_usage
                    db.session.commit()

                    next_run_delay = conf.fitter.min_tenant_interval if tenant_usage else conf.fitter.tenant_interval

                    logbook.debug("Create mutex for tenant {} to prevent very often access to ceilometer. Delay: {}",
                                  tenant, next_run_delay)
            if next_run_delay and not conf.test:
                mutex = TenantMutex(tenant)
                mutex.acquire(ttl_ms=next_run_delay * 1000)

        db.session.close()

        logbook.info("Usage collection run complete.")
        return usage

    @staticmethod
    def filter_and_group(usage):
        usage_by_resource = defaultdict(list)
        with timed("filter and group by resource"):
            trust_sources = set(conf.fitter.trust_sources)
            for u in usage:
                # the user can make their own samples, including those
                # that would collide with what we care about for
                # billing.
                # if we have a list of trust sources configured, then
                # discard everything not matching.
                if trust_sources and u.source not in trust_sources:
                    logbook.warning('ignoring untrusted usage sample from source `{}`', u['source'])
                    continue

                resource_id = u.resource_id
                usage_by_resource[resource_id].append(u)
        return usage_by_resource

    def collect_usage(self, tenant, mutex, end=None):
        # Collects usage for a given tenant from when they were last collected,
        #   up to the given end, and breaks the range into one hour windows.
        end = end or datetime.utcnow()

        time_label = TimeLabel(tenant.last_collected + timedelta(minutes=1))
        end_time_label = TimeLabel(end)
        usage = {}
        logbook.info('collect_usage for {}, from {} till {} (last_collected: {})',
                     tenant, time_label, end_time_label, tenant.last_collected)

        customer = Customer.get_by_tenant_id(tenant.tenant_id)
        if not customer:
            logbook.error("Customer for tenant {} not found", tenant)
            return usage

        while time_label < end_time_label:
            try:
                usages = self._collect_usage(tenant, time_label, customer)
                tenant.last_collected = time_label.datetime_range()[1]
                if usages:
                    db.session.add(customer)
                    total_cost = customer.calculate_usage_cost(usages)
                    customer.withdraw(total_cost)
                    if not conf.test:
                        db.session.commit()

                    usage[time_label] = [usage.to_dict() for usage in usages], total_cost
            except Exception:
                self.errors += 1
                import traceback

                traceback.print_exc()
                logbook.exception("Usage process failed for {} and {}", tenant, time_label)
                db.session.rollback()
                return usage

            time_label = time_label.next()
            mutex.update_ttl()
        return usage

    @staticmethod
    def sort_entries(data):
        """
        Setup timestamps as datetime objects,
        and sort.
        """
        for entry in data:
            timestamp = entry.timestamp
            if isinstance(timestamp, datetime):
                continue
            try:
                # noinspection PyTypeChecker
                timestamp = datetime.strptime(timestamp, date_format)
            except ValueError:
                timestamp = datetime.strptime(timestamp, other_date_format)
            entry.timestamp = timestamp
        return sorted(data, key=attrgetter("timestamp"))

    def _collect_usage(self, tenant, time_label, customer):
        mappings = conf.fitter.collection.meter_mappings

        processed_usage = []
        for meter_name, meter_info in sorted(mappings.items()):
            start, end = time_label.datetime_range()
            usage = openstack_wrapper.openstack.get_tenant_usage(tenant.tenant_id,
                                                                 meter_name,
                                                                 start - self.window_leading,
                                                                 end + self.window_leading)
            usage = self.sort_entries(usage)

            if not usage:
                continue

            if 'service' in meter_info:
                service = meter_info['service']
            else:
                service = meter_name

            processed_usage.extend(self.transform_usage(tenant, usage, service, meter_info, time_label, customer))

        return processed_usage

    def transform_usage(self, tenant, usage, service, meter_info, time_label, customer):
        transformed_usage = []
        usage_by_resource = self.filter_and_group(usage)
        transformer_name = meter_info['transformer']
        transformer_args = {}
        if isinstance(transformer_name, dict):
            assert len(transformer_name) == 1
            transformer_name, transformer_args = next(iter(transformer_name.items()))
        transformer = get_transformer(transformer_name, **transformer_args)

        for resource_id, entries in usage_by_resource.items():
            # apply the transformer.
            try:
                transformed = transformer.transform_usage(service, entries, time_label)
            except Exception as e:
                logbook.warning("Error {} during processing usage for tenant {}, service: {}, "
                                "meter_info: {}, time_label: {}, resource_id: {}: {}",
                                e, tenant, service, meter_info, time_label, resource_id, entries)
                raise

            for su in transformed:
                service_usage = ServiceUsage(tenant.tenant_id, su.service_id, time_label, resource_id,
                                             customer.tariff, su.volume, su.start, su.end,
                                             resource_name=su.resource_name)
                db.session.add(service_usage)
                transformed_usage.append(service_usage)
        return transformed_usage
