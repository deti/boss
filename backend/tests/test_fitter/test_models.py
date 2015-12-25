import datetime
from tests.base import BaseTestCaseDB
from model import db, Tenant


class TestDb(BaseTestCaseDB):
    def test_create_tenant(self):
        t = Tenant(tenant_id="asfd", name="test", created=datetime.datetime.utcnow(),
                   last_collected=datetime.datetime.utcnow())
        db.session.add(t)
        db.session.commit()
        t2 = db.session.query(Tenant).get("asfd")
        self.assertTrue(t2.name == "test")
