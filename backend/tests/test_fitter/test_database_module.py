# -*- coding: utf-8 -*-
import json
from datetime import timedelta, datetime
from tests.base import FitterTestBase
from model import db, Tenant


class TestDatabaseModule(FitterTestBase):

    def fill_db(self, numb_tenants, numb_resources, now):
        session = db.session
        for i in range(numb_tenants):
            session.add(Tenant(
                id="tenant_id_" + str(i),
                info="metadata",
                name="tenant_name_" + str(i),
                created=now,
                last_collected=now
            ))
            db.session.flush()
        db.session.commit()
