import conf
import logbook
from model import db, AccountDb
from sqlalchemy import Column, ForeignKey, or_
from utils.croniter import croniter
from arrow import utcnow
from datetime import datetime, timedelta


class ScheduledTask(db.Model, AccountDb):
    id_field = "customer_id"
    unique_field = "email"

    task_id = Column(db.Integer, primary_key=True)
    task_name = Column(db.String(64), index=True)
    customer_id = Column(db.Integer, ForeignKey("customer.customer_id", ondelete="CASCADE"), index=True)
    started = Column(db.DateTime(), index=True)
    next_scheduled = Column(db.DateTime(timezone=True), index=True)
    frequency = Column(db.String(64), nullable=False)
    last = Column(db.DateTime(), index=True)

    default_cron_data = {"MIN": 0, "HOUR": 0, "DAY": 1, "WEEK_DAY": 1}

    def __init__(self, task_name, customer_id, frequency, cron_data=None, now=None):
        self.task_name = task_name
        self.customer_id = customer_id
        cron_frequency = self.cron_frequency(frequency, cron_data)
        logbook.debug("Setup task {} for customer {} with frequency: {}", task_name, customer_id, cron_frequency)
        now = now or utcnow().datetime
        try:
            cron = croniter(cron_frequency, start_time=now)
        except ValueError as e:
            logbook.error("Invalid frequency format {}: {}", cron_frequency, e)
            raise

        self.frequency = cron_frequency
        self.started = None
        self.next_scheduled = cron.get_next(datetime)
        self.last = now

    def cron_frequency(self, frequency, cron_data=None):
        data = self.default_cron_data.copy()
        conf_data = conf.event.event[self.task_name].get("periods", {}).get(frequency)
        if conf_data:
            data.update(conf_data)
        if cron_data:
            data.update(cron_data)
        cron_frequency = conf.event.period[frequency]["cron"]
        return cron_frequency.format(**data)

    def update_period(self, frequency, cron_data=None, now=None):
        cron_frequency = self.cron_frequency(frequency, cron_data=cron_data)
        now = now or utcnow().datetime
        try:
            cron = croniter(cron_frequency, start_time=now)
        except ValueError as e:
            logbook.error("Invalid frequency format {}: {}", cron_frequency, e)
            raise

        self.frequency = cron_frequency
        self.next_scheduled = cron.get_next(datetime)

    @classmethod
    def scheduled_tasks(cls, task_name, now=None, query=None):
        from model import Customer
        task_config = conf.event.event[task_name]
        now = now or utcnow().datetime
        now = now.replace(microsecond=0)

        query = query or cls.query

        query = query.filter(cls.task_name == task_name,
                             cls.next_scheduled < now,
                             or_(cls.started == None,
                                 cls.started < now - timedelta(seconds=task_config["task_hang"])))
        query = query.filter(cls.customer_id == Customer.customer_id).limit(task_config["limit"])
        return query

    @classmethod
    def get_by_customer(cls, customer_id, task_name):
        return cls.query.filter_by(customer_id=customer_id, task_name=task_name).first()

    def start(self, now=None, autocommit=True):
        self.started = now or utcnow().datetime
        if autocommit:
            db.session.commit()

    def completed(self, move_ahead=True, now=None):
        now = now or utcnow().datetime
        task_str = str(self)
        self.started = None
        if move_ahead:
            _, next_send = self.task_range(now)
            self.next_scheduled = next_send
            self.last = now
            logbook.info("Completed task {} and scheduled next at {}", task_str, next_send)
        else:
            logbook.info("Task {} failed and it will be rescheduled", task_str)
        db.session.flush()
        logbook.info("Task after prolongation {}", self)
        db.session.commit()

    def task_range(self, base_time=None, previous_interval=False, next_interval=False):
        if base_time is None:
            base_time = utcnow().datetime

        # Because croniter doesn't take seconds into account, add 1 minute
        base_time += timedelta(minutes=1)
        cron = croniter(self.frequency, base_time)
        if previous_interval:
            cron.get_prev(datetime)
        elif next_interval:
            cron.get_next(datetime)
            cron.get_next(datetime)
        return cron.get_prev(datetime), cron.get_next(datetime)

    @classmethod
    def remove_by_customer_id(cls, customer_id):
        return cls.query.filter_by(customer_id=customer_id).delete(False)
