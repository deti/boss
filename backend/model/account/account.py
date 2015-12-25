import conf
from model import db, AccountDb, Customer
from sqlalchemy import Column, ForeignKey
from sqlalchemy.orm import relationship, Load
from decimal import Decimal
from arrow import utcnow


class Account(db.Model, AccountDb):
    id_field = "account_id"

    account_id = Column(db.Integer, primary_key=True)
    customer_id = Column(db.Integer, ForeignKey("customer.customer_id"))
    currency = Column(db.String(3))
    balance = Column(db.DECIMAL(precision=conf.backend.decimal.precision, scale=conf.backend.decimal.scale))
    withdraw = Column(db.DECIMAL(precision=conf.backend.decimal.precision, scale=conf.backend.decimal.scale))

    history = relationship("AccountHistory", lazy="dynamic")

    def __str__(self):
        return "<Account {0.account_id} {0.customer_id} {0.currency} {0.balance}>".format(self)

    @classmethod
    def create(cls, currency, customer, user_id, comment="create new account", start_balance=Decimal(0)):
        account = cls()
        account.currency = currency
        account.balance = start_balance
        account.withdraw = Decimal(0)
        db.session.flush()

        account.history.append(AccountHistory.create(customer, account.account_id, user_id, comment, start_balance))

        return account

    def modify(self, customer, delta, user_id, comment, transaction_id=None):
        self.balance = Account.balance + delta
        self.history.append(AccountHistory.create(customer, self.account_id, user_id, comment, delta, transaction_id=transaction_id))
        db.session.flush()

    def charge(self, delta):
        self.withdraw = Account.withdraw + delta
        db.session.flush()

    @property
    def current(self):
        return self.balance - self.withdraw


class AccountHistory(db.Model, AccountDb):
    id_field = "account_history_id "

    account_history_id = Column(db.Integer, primary_key=True)
    customer_id = Column(db.Integer, ForeignKey("customer.customer_id"))
    account_id = Column(db.Integer, ForeignKey("account.account_id"))
    comment = Column(db.Text())
    user_id = Column(db.Integer, ForeignKey("user.user_id"))
    delta = Column(db.DECIMAL(precision=conf.backend.decimal.precision, scale=conf.backend.decimal.scale))
    date = Column(db.DateTime, index=True)
    customer_mode = Column(Customer.CUSTOMER_MODE, nullable=False)
    transaction_id = Column(db.Integer, index=True)

    display_fields = frozenset(["comment", "delta", "date"])

    user = relationship("User")
    account = relationship("Account")

    def __str__(self):
        return "<AccountHistory %s %s '%s'>" % (self.account_id, self.delta, self.comment)

    @classmethod
    def create(cls, customer, account_id, user_id, comment, delta, date=None, transaction_id=None):
        history = cls()
        history.customer_id = customer.customer_id
        history.account_id = account_id
        history.user_id = user_id
        history.comment = comment
        history.delta = delta
        history.date = date or utcnow().datetime
        history.customer_mode = customer.customer_mode
        history.transaction_id = transaction_id

        return history

    def display(self, short=True):
        res = super().display(short)
        if not short and self.user_id:
            res["user"] = self.user.display(short)
        res["currency"] = self.account.currency
        return res

    @classmethod
    def report(cls, start, finish, only_income=True):
        query = db.session.query(Customer, AccountHistory, Account).\
            filter(AccountHistory.customer_id == Customer.customer_id,
                   AccountHistory.account_id == Account.account_id,
                  ((AccountHistory.customer_mode == Customer.CUSTOMER_PRODUCTION_MODE) |
                   (AccountHistory.customer_mode == Customer.CUSTOMER_PENDING_PRODUCTION_MODE)))
        query = query.filter(cls.date >= start, cls.date < finish)
        if only_income:
            query = query.filter(cls.delta >= 0)

        query = query.options(Load(Customer).load_only("email"))
        query = query.options(Load(Account).load_only("currency"))
        query = query.options(Load(AccountHistory).load_only("date", "comment", "delta", "user_id"))

        query = query.order_by(cls.customer_id)

        return query

    @classmethod
    def get_by_transaction_id(cls, transaction_id):
        return cls.query.filter(cls.transaction_id == transaction_id)

