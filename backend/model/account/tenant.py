# -*- coding: utf-8 -*-
import logbook
from arrow import utcnow
from sqlalchemy import Column, String, Text, DateTime
from model import db, AccountDb


class Tenant(db.Model, AccountDb):
    """Model for storage of metadata related to a tenant."""

    # ID is a uuid
    tenant_id = Column(String(32), primary_key=True, nullable=False)
    name = Column(Text, nullable=False)
    created = Column(DateTime, nullable=False)
    last_collected = Column(DateTime)
    deleted = Column(db.DateTime())

    @classmethod
    def create(cls, tenant_id, tenant_name, created_at=None):
        created_at = created_at or utcnow().datetime
        tenant = cls()
        tenant.tenant_id = tenant_id
        tenant.name = tenant_name
        tenant.created = created_at or utcnow().datetime
        tenant.last_collected = created_at
        db.session.add(tenant)
        db.session.flush()           # can't assume deferred constraints.
        return tenant

    def __str__(self):
        return "<Tenant %s %s>" % (self.tenant_id, self.name)

    @classmethod
    def all_active_tenants(cls):
        return cls.query.filter_by(deleted=None)

    def mark_removed(self):
        logbook.info("Remove {} from db", self)
        self.deleted = utcnow().datetime
