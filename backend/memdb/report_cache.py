import conf
import logbook
import msgpack
import datetime
from memdb import MemDbModel
from decimal import Decimal
from utils.money import decimal_to_string
from celery.result import AsyncResult
from celery import states as celery_states
from arrow import utcnow


def default_json(obj):
    if isinstance(obj, Decimal):
        return decimal_to_string(obj)
    if isinstance(obj, datetime.datetime):
        return {"$datetime$": obj.replace(microsecond=0).isoformat()}
    if isinstance(obj, datetime.date):
        return {"$date$": obj.isoformat()}
    if hasattr(obj, "to_json"):
        return obj.to_json()
    raise TypeError("Cannot serialize %r" % obj)


def object_hook_datetime(obj):
    if len(obj) == 1:
        if "$date$" in obj:
            try:
                return datetime.datetime.strptime(obj["$date$"], "%Y-%m-%d").date()
            except ValueError:
                logbook.warning("can't decode obj {} as date: {}", obj, e)
                return obj
        elif "$datetime$" in obj:
            try:
                val = obj["$datetime$"]
                val = val.split("+", 1)[0]
                return datetime.datetime.strptime(val, "%Y-%m-%dT%H:%M:%S")
            except ValueError as e:
                logbook.warning("can't decode obj {} as datetime: {}", obj, e)
                return obj
    return obj


class ReportId(object):
    def __init__(self, start, end, report_type, report_format, locale):
        self.start = start
        self.end = end
        self.report_type = report_type
        self.report_format = report_format
        self.locale = locale

    @staticmethod
    def isoformat(date):
        if date is not None:
            return date.isoformat()
        return ""

    @property
    def key(self):
        return ":".join((self.report_format, self.report_type, str(self.locale),
                         self.isoformat(self.start), self.isoformat(self.end)))

    @property
    def aggregation_key(self):
        return ":".join(("agg", self.report_type, str(self.locale),
                         self.isoformat(self.start), self.isoformat(self.end)))

    def __str__(self):
        return "<Report %s:%s (%s) [%s-%s]>" % (self.report_type, self.report_format, self.locale, self.start, self.end)

    def __repr__(self):
        return str(self)

    def replace(self, **kwargs):
        new = ReportId(self.start, self.end, self.report_type, self.report_format, self.locale)
        for key, value in kwargs.items():
            setattr(new, key, value)
        return new


class CustomerReportId(ReportId):
    def __init__(self, customer_id, start, end, report_type, report_format, locale):
        super().__init__(start, end, report_type, report_format, locale)
        self.customer_id = customer_id

    def __str__(self):
        return "<Report %s %s:%s (%s) [%s-%s]>" % (self.customer_id, self.report_type,
                                                   self.report_format, self.locale, self.start, self.end)

    @property
    def key(self):
        return ":".join((str(self.customer_id), self.report_format, self.report_type, str(self.locale),
                         self.start.isoformat(), self.end.isoformat()))

    @property
    def aggregation_key(self):
        return ":".join(("agg", str(self.customer_id), self.report_type,
                         str(self.locale), self.start.isoformat(), self.end.isoformat()))


class ReportTask(MemDbModel):
    _prefix = "report:task:"

    def key(self, report_id):
        return self._prefix + report_id.key

    def get(self, report_id):
        return self.redis.get(self.key(report_id))

    def set(self, report_id, task_id):
        return self.redis.setex(self.key(report_id), conf.report.report_task_store_time, task_id)

    def remove(self, report_id):
        logbook.info("Removing task for {}", report_id)
        return self.redis.delete(self.key(report_id))

    def task_status(self, report_id):
        task_id = self.get(report_id)
        if task_id:
            result = AsyncResult(task_id)
            logbook.info("Task status for {}: {}", report_id, result.state)
            if result.state == celery_states.FAILURE:
                status = "error"
                self.remove(report_id)
            else:
                status = "in progress"
            return status
        return None


class ReportCache(MemDbModel):
    """ Used for storing aggregated reports in cache
    """
    _prefix = "report:"

    def key(self, report_id):
        return self._prefix + report_id.key

    def aggregation_key(self, report_id):
        return self._prefix + report_id.aggregation_key

    def get_report(self, report_id):
        res = self.redis.get(self.key(report_id))
        if res:
            logbook.debug("Extract report {}. Size: {}", report_id, len(res))
        else:
            logbook.debug("Report for {} not found. Key: {}", report_id, self.key(report_id))
        return res

    def set_report(self, report_id, data, cache_time=None):
        assert isinstance(data, bytes)
        logbook.debug("Store report {}. Size: {}. Key: {}", report_id, len(data), self.key(report_id))
        self.redis.setex(self.key(report_id), cache_time or conf.report.report_store_time, data)

    @staticmethod
    def pack_aggregated(aggregated):
        return msgpack.packb(aggregated, default=default_json, use_bin_type=True)

    @staticmethod
    def unpack_aggregated(packed):
        try:
            return msgpack.unpackb(packed, object_hook=object_hook_datetime, encoding='utf-8')
        except Exception as e:
            logbook.error("Invalid binary report: {}".format(e))
            return None

    def get_report_aggregated(self, report_id):
        res = self.redis.get(self.aggregation_key(report_id))
        if res is None:
            return None

        return self.unpack_aggregated(res)

    def set_report_aggregated(self, report_id, aggregated, cache_time=None):
        data = self.pack_aggregated(aggregated)

        if cache_time is None:
            if report_id.end is not None and report_id.end > utcnow():
                cache_time = conf.report.cache_time.short  # used for tests
            else:
                cache_time = conf.report.cache_time.current_stat
        self.redis.setex(self.aggregation_key(report_id), cache_time, data)
