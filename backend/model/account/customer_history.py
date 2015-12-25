import json
import conf
from model import db, AccountDb
from sqlalchemy import Column, ForeignKey
from sqlalchemy.orm import relationship, deferred
from arrow import utcnow
from utils import DateTimeJSONEncoder


class CustomerHistory(db.Model, AccountDb):
    id_field = "customer_history_id"

    EVENT_CREATED = "created"
    EVENT_CHANGE_TARIFF = "tariff"
    EVENT_REMOVE = "deleted"
    EVENT_CHANGE_INFO = "info"
    EVENT_BLOCK = "block"
    EVENT_UNBLOCK = "unblock"
    EVENT_RESET_EMAIL = "reset_email"
    EVENT_RESET_PASSWORD = "reset_password"
    EVENT_CONFIRM_EMAIL = "confirm_email"
    EVENT_EMAIL_CONFIRMED = "email_confirmed"
    EVENT_MAKE_PROD = "make_prod"
    EVENT_PENDING_PROD = "pending_prod"
    EVENT_QUOTA_CHANGED = "changed_quotas"
    EVENT_CHANGE_PASSWORD = "change_password"

    customer_history_id = Column(db.Integer, primary_key=True)
    customer_id = Column(db.Integer, ForeignKey("customer.customer_id", ondelete="CASCADE"), index=True)
    user_id = Column(db.Integer, ForeignKey("user.user_id", ondelete="set null"))
    comment = Column(db.Text())
    event = Column(db.Text())
    date = Column(db.DateTime, index=True)
    snapshot = deferred(Column(db.Text()))

    display_fields = frozenset(["comment", "date", "snapshot", "event", "localized_name"])
    display_fields_short = frozenset(["comment", "date", "event", "localized_name"])

    customer = relationship("Customer")
    user = relationship("User")

    def __str__(self):
        return "<CustomerHistory %s %s %s>" % (self.customer.get_name() if self.customer else None,
                                               self.event, self.date)

    @classmethod
    def create(cls, event, customer, user_id, comment, date=None):
        history = cls()
        history.customer_id = customer.customer_id
        history.event = event
        history.user_id = user_id
        history.comment = comment
        history.date = date or utcnow().datetime
        snapshot = customer.display(short=True)
        snapshot["subscription"] = customer.subscription_info()
        snapshot.pop("account", None)
        snapshot = json.dumps(snapshot, cls=DateTimeJSONEncoder)
        history.snapshot = snapshot
        db.session.add(history)
        db.session.flush()
        return history

    @classmethod
    def tariff_changed(cls, customer, user_id, comment, date=None):
        return cls.create(cls.EVENT_CHANGE_TARIFF, customer, user_id, comment, date)

    @classmethod
    def new_customer(cls, customer, user_id, comment, date=None):
        return cls.create(cls.EVENT_CREATED, customer, user_id, comment, date)

    @classmethod
    def remove_customer(cls, customer, user_id, comment, date=None):
        return cls.create(cls.EVENT_REMOVE, customer, user_id, comment, date)

    @classmethod
    def change_info(cls, customer, user_id, comment, date=None):
        return cls.create(cls.EVENT_CHANGE_INFO, customer, user_id, comment, date)

    @classmethod
    def blocked(cls, blocked, customer, user_id, comment, date=None):
        event = cls.EVENT_BLOCK if blocked else cls.EVENT_UNBLOCK
        return cls.create(event, customer, user_id, comment, date)

    def display(self, short=True):
        res = super().display(short)
        res["user"] = self.user.display(short=True) if self.user else None
        if not short:
            res["snapshot"] = json.loads(res["snapshot"])
        return res

    @property
    def localized_name(self):
        return conf.customer.events.get(self.event)

    @classmethod
    def reset_password_email(cls, customer, comment, date=None):
        return cls.create(cls.EVENT_RESET_EMAIL, customer, None, comment, date)

    @classmethod
    def reset_password(cls, customer, comment, date=None):
        return cls.create(cls.EVENT_RESET_PASSWORD, customer, None, comment, date)

    @classmethod
    def send_confirm_email(cls, customer, user_id, comment, date=None):
        return cls.create(cls.EVENT_CONFIRM_EMAIL, customer, user_id, comment, date)

    @classmethod
    def email_confirmed(cls, customer, comment, date=None):
        return cls.create(cls.EVENT_EMAIL_CONFIRMED, customer, None, comment, date)

    @classmethod
    def make_prod(cls, customer, user_id, comment, date=None):
        return cls.create(cls.EVENT_MAKE_PROD, customer, user_id, comment, date)

    @classmethod
    def make_pending_prod(cls, customer, user_id, comment, date=None):
        return cls.create(cls.EVENT_PENDING_PROD, customer, user_id, comment, date)

    @classmethod
    def quota_changed(cls, customer, user_id, comment, date=None):
        return cls.create(cls.EVENT_QUOTA_CHANGED, customer, user_id, comment, date)

    @classmethod
    def change_password(cls, customer, comment, date=None):
        return cls.create(cls.EVENT_CHANGE_PASSWORD, customer, None, comment, date)

    @classmethod
    def get_last_block_event(cls, customer):
        block_event = cls.query.filter_by(customer_id=customer.customer_id, event=CustomerHistory.EVENT_BLOCK)\
            .order_by(-CustomerHistory.customer_history_id).first()
        return block_event
