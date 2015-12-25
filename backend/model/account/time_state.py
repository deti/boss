import conf
import logbook
from model import db, AccountDb
from sqlalchemy import Column, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from arrow import utcnow
from datetime import timedelta
from utils import find_first


class TimeState(db.Model, AccountDb):
    time_state_id = Column(db.Integer, primary_key=True)
    name = Column(db.String(64), nullable=False)
    customer_id = Column(db.Integer, ForeignKey("customer.customer_id", ondelete="CASCADE"), nullable=False)
    scheduled_at = Column(db.DateTime(), index=True, nullable=False)
    action = Column(db.String(64), nullable=False)
    step = Column(db.Integer)

    customer = relationship("Customer")

    __table_args__ = (UniqueConstraint('customer_id', 'name'),)

    def __str__(self):
        return "<TimeState %s of %s. %s scheduled at %s>" % (self.name, self.customer, self.action, self.scheduled_at)

    def __init__(self, name, customer_id, scheduled_at, action):
        self.name = name
        self.customer_id = customer_id
        self.scheduled_at = scheduled_at
        self.action = action
        self.step = 0

    @classmethod
    def get_actual_actions(cls, now=None):
        now = now or utcnow().datetime
        return cls.query.filter(cls.scheduled_at < now)

    def remove(self):
        db.session.delete(self)

    @classmethod
    def get_by_customer(cls, customer_id, name):
        return cls.query.filter(cls.customer_id == customer_id, cls.name == name).first()


class TimeMachine(object):
    name = None
    schedule = None
    machines = {}

    @classmethod
    def add_machine(cls, machine):
        cls.machines[machine.name] = machine

    @classmethod
    def create(cls, customer_id, restart_existed=False):
        assert cls.name
        assert cls.schedule is not None

        first_action, delay = cls.schedule[0]
        scheduled_at = utcnow().datetime + timedelta(seconds=delay)
        state = TimeState.get_by_customer(customer_id, cls.name)
        if state:
            if not restart_existed:
                return
        else:
            state = TimeState(cls.name, customer_id, scheduled_at, first_action)
        logbook.info("Created time machine {} for {}", cls.name, customer_id)
        db.session.add(state)

    @classmethod
    def make_action(cls, state, now=None):
        from model import Customer
        logbook.info("Try apply action: {}", state)

        now = now or utcnow().datetime

        machine = cls.machines[state.name]
        customer = Customer.get_by_id(state.customer_id)
        try:
            new_state_name = getattr(machine, state.action)(customer)
        except Exception as e:
            logbook.error("action {} failed: {}", state, e)
            state.remove()
            db.session.commit()
            raise

        state.step += 1
        if not new_state_name:
            if state.step >= len(machine.schedule):
                logbook.info("Actions {} are completed for {}", cls.name, customer)
                state.remove()
                db.session.commit()
                return

            new_state = machine.schedule[state.step]
        else:
            new_state = find_first(machine.schedule, lambda x: x[0] == new_state_name)
            if not new_state:
                state.remove()
                db.session.commit()
                raise Exception("Can't find new state %s for machine %s" % (new_state_name, cls.name))
        state.action = new_state[0]
        state.scheduled_at = now + timedelta(seconds=new_state[1])
        logbook.info("New action {} is scheduled", state)

    @classmethod
    def check(cls, now=None):
        count = 0

        for state in TimeState.get_actual_actions(now):
            cls.make_action(state, now)
            db.session.commit()
            count += 1
        return count

    @classmethod
    def stop(cls, customer_id):
        state = TimeState.get_by_customer(customer_id, cls.name)
        if state:
            state.remove()


class TestPeriodOver(TimeMachine):
    name = "test_period_over"
    schedule = [
        ("block", conf.customer.test_customer.test_period.blocking),
        ("remove_resources", conf.customer.test_customer.test_period.removing_resource)
    ]

    @classmethod
    def block(cls, customer):
        customer.block(True, None, "Test period is over")

    @classmethod
    def remove_resources(cls, customer):
        from task.openstack import delete_only_resources
        if customer.os_tenant_id:
            delete_only_resources(customer.os_tenant_id)


class BlockCustomer(TimeMachine):
    name = "block_customer"
    schedule = [tuple(state.items())[0] for state in conf.customer.blocking.schedule]

    @classmethod
    def shut_off_vms(cls, customer):
        from task.openstack import stop_instances
        stop_instances(customer.os_tenant_id)

    @classmethod
    def remove_floating_ips(cls, customer):
        from task.openstack import delete_floating_ips
        delete_floating_ips(customer.os_tenant_id)

    @classmethod
    def hdd_remove_notification(cls, customer):
        from task.notifications import notify_managers_about_hdd
        notify_managers_about_hdd(customer.customer_id)

    @classmethod
    def final_delete(cls, customer):
        customer.remove(None, 'Final deleting of OpenStack resources')


TimeMachine.add_machine(TestPeriodOver)
TimeMachine.add_machine(BlockCustomer)
