import logbook
from model import db, AccountDb, Customer, autocommit
from sqlalchemy import Column, ForeignKey
from sqlalchemy.orm import relationship
from arrow import utcnow


class Deferred(db.Model, AccountDb):
    id_field = "deferred_id"

    deferred_id = Column(db.Integer, primary_key=True)
    user_id = Column(db.Integer, ForeignKey("user.user_id"))
    customer_id = Column(db.Integer, ForeignKey("customer.customer_id"), unique=True)
    tariff_id = Column(db.Integer, ForeignKey("tariff.tariff_id"))
    date = Column(db.DateTime(), index=True)
    comment = Column(db.Text())

    tariff = relationship("Tariff")
    user = relationship("User")
    customer = relationship("Customer")

    def __str__(self):
        return "<Deferred %s %s>" % (self.tariff.name, self.date)

    def __repr__(self):
        return str(self)

    @classmethod
    def create(cls, customer_id, tariff_id, user_id, date, comment):
        deferred = cls.query.filter_by(customer_id=customer_id).first()
        if not deferred:
            deferred = cls()
            deferred.customer_id = customer_id
            db.session.add(deferred)
        deferred.tariff_id = tariff_id
        deferred.user_id = user_id
        deferred.date = date
        deferred.comment = comment

        return deferred

    @classmethod
    def find_deferred(cls, now=None):
        now = now or utcnow()
        return cls.query.filter(cls.date <= now)

    def display(self, short=True):
        return {"tariff": self.tariff.display(short=True),
                "date": self.date,
                "user": self.user.display(),
                "comment": self.comment
                }

    @classmethod
    def delete_by_customer(cls, customer_id):
        return cls.query.filter_by(customer_id=customer_id).delete(False)

    @classmethod
    def get_by_customer(cls, customer_id):
        return cls.query.filter_by(customer_id=customer_id).first()

    @classmethod
    def process_pending_deferred_changes(cls, time_now=None, name_prefix=""):
        db.session.rollback()
        logbook.debug("Process pending deferred changes task for customer prefix {} and time {}", name_prefix, time_now)
        time_now = time_now or utcnow().datetime
        query = cls.find_deferred(time_now)
        if name_prefix:
            customer_ids = [c.customer_id for c in Customer.get_customers_by_prefix_info_field(name_prefix, "name")]
            query = query.filter(cls.customer_id.in_(customer_ids)) if customer_ids else []

        count = 0
        for deferred in query:
            cls.do_deferred_changes(deferred)
            count += 1
        logbook.debug("Processed {} pending deferred changes", count)

        db.session.commit()
        return count

    @classmethod
    @autocommit
    def do_deferred_changes(cls, deferred_changes):
        logbook.info("Process pending deferred change {}", deferred_changes)

        deferred_changes.customer.update_tariff(deferred_changes.tariff_id,
                                                deferred_changes.user_id,
                                                deferred_changes.comment)
        Deferred.delete_by_customer(deferred_changes.customer_id)
