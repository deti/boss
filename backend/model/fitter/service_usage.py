# -*- coding: utf-8 -*-
import conf
from sqlalchemy import Column, DateTime, String, Integer, func, BigInteger, UniqueConstraint
from fitter.aggregation.timelabel import TimeLabel
from model import db, FitterDb, Customer
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import timedelta


class ServiceUsage(db.Model, FitterDb):
    # __bind_key__ = "fitter"
    service_usage_id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(100), nullable=False)
    service_id = Column(String(100), nullable=False)
    time_label = Column(String(TimeLabel.label_length), index=True, nullable=False, primary_key=True)
    resource_id = Column(String(100), nullable=False)
    resource_name = Column(String(256), nullable=True)

    __table_args__ = (UniqueConstraint('tenant_id', 'service_id', 'time_label', 'resource_id'), )

    volume = Column(BigInteger, nullable=True)
    start = Column(DateTime, nullable=False)
    tariff_id = Column(Integer, index=True)
    end = Column(DateTime, nullable=False)
    currency = Column(db.String(3))
    customer_mode = Column(Customer.CUSTOMER_MODE)

    cost = Column(db.DECIMAL(precision=conf.backend.decimal.precision, scale=conf.backend.decimal.scale))
    usage_volume = Column(BigInteger)

    def __init__(self, tenant_id, service_id, time_label, resource_id, tariff, volume, start, end, resource_name=None):
        self.tenant_id = tenant_id
        self.service_id = service_id
        self.tariff_id = None
        self.time_label = time_label.label
        self.resource_id = resource_id
        self.volume = int(volume)
        self.start = start
        self.end = end
        self.cost = None
        self.usage_volume = None
        self.tariff_id = tariff.tariff_id
        self.currency = tariff.currency
        self.customer_mode = None
        self.resource_name = resource_name

    def __str__(self):
        return "<Usage {0.time_label} {0.tenant_id} {0.service_id} {0.resource_id} {0.currency} {0.volume} {0.length}>".format(self)

    @hybrid_property
    def length(self):
        return self.end - self.start + timedelta(seconds=1)

    @classmethod
    def get_usage(cls, customer, start, finish):
        tenant_id = customer.os_tenant_id

        start_tl = TimeLabel(start).label
        finish_tl = TimeLabel(finish).label
        query = db.session.query(cls.service_id, cls.tariff_id, func.sum(cls.cost), func.sum(cls.usage_volume)).\
            filter(cls.tenant_id == tenant_id, cls.time_label >= start_tl, cls.time_label < finish_tl)
        query = query.group_by(cls.tariff_id, cls.service_id)
        return query

    @classmethod
    def get_detailed_usage(cls, customer, start, finish):
        tenant_id = customer.os_tenant_id

        start_tl = TimeLabel(start).label
        finish_tl = TimeLabel(finish).label
        query = cls.query.filter(cls.tenant_id == tenant_id, cls.time_label >= start_tl, cls.time_label < finish_tl)
        return query

    @classmethod
    def get_withdraw(cls, customer, start, finish):
        start_tl = TimeLabel(start).label
        finish_tl = TimeLabel(finish).label
        query = db.session.query(cls.currency, func.sum(cls.cost)).\
            filter(cls.tenant_id == customer.os_tenant_id, cls.time_label >= start_tl, cls.time_label < finish_tl)
        query = query.group_by(cls.currency)
        return dict(query)

    @classmethod
    def customers_get_usage(cls, start, finish):
        from model import Customer
        start_tl = TimeLabel(start).label
        finish_tl = TimeLabel(finish).label
        deleted_gap = timedelta(seconds=conf.report.deleted_gap)
        active_customers = Customer.query.filter((Customer.deleted == None) |
                                                 (Customer.deleted < start -  deleted_gap))

        result = {}
        for customer in active_customers:
            if customer.os_tenant_id:
                query = db.session.query(cls.currency, func.sum(cls.cost)).\
                    filter(cls.tenant_id == customer.os_tenant_id,
                           cls.time_label >= start_tl, cls.time_label < finish_tl)
                query = query.group_by(cls.currency)
                result[customer] = query.all()
        return result

