from arrow import utcnow
import errors
from tests.base import BaseTestCaseDB, TestCaseApi, format_api_date
from model import Tariff, db, TariffHistory, User, ServicePrice
from decimal import Decimal
from copy import deepcopy
from datetime import timedelta


class TestTariff(BaseTestCaseDB):
    def test_tariff_create(self):
        lname = self.localized_name("tariff1")
        Tariff.create_tariff(lname, "tariff!!!", "RUB", None)
        db.session.commit()

        with self.assertRaises(errors.TariffAlreadyExists):
            Tariff.create_tariff(lname, "tariff!!!", "RUB", None)
        db.session.rollback()

        Tariff.create_tariff({"en": "tt", "ru": "tt"}, "tariff!!!", "RUB", None)

        name = lname.copy()
        name["en"] = "xxxx"
        with self.assertRaises(errors.TariffAlreadyExists):
            Tariff.create_tariff(name, "tariff!!!", "RUB", None)
        db.session.rollback()

        name = lname.copy()
        name["ru"] = "xxxx"
        with self.assertRaises(errors.TariffAlreadyExists):
            Tariff.create_tariff(name, "tariff!!!", "RUB", None)
        db.session.rollback()

        name["ru"] = lname["en"]
        name["en"] = lname["ru"]
        Tariff.create_tariff(name, "tariff!!!", "RUB", None)

    def test_tariff_update(self):
        lname = self.localized_name("tariff_update")
        tariff = Tariff.create_tariff(lname, "Tariff Update", "RUB", None)
        db.session.commit()

        tariff.update({"tr": "Tariffo"})
        db.session.commit()

        tariff.update({"en": "Super Tariff"})
        tariff.update(description="new description")
        db.session.commit()

        t = Tariff.get_by_id(tariff.tariff_id)
        localizations = {l.language: l for l in t.localized_name}
        self.assertEqual(localizations["en"].localized_name, "Super Tariff")
        self.assertEqual(localizations["tr"].localized_name, "Tariffo")
        self.assertEqual(t.description, "new description")

    def test_tariff_add_service(self):
        t = Tariff.create_tariff(self.localized_name("tariff_and_services"), "Test tariff with services", "RUB", None)
        t.update(services=[{"service_id": "m1.small", "price": "12.3456"}])
        db.session.commit()

        tt = Tariff.get_by_id(t.tariff_id)
        self.assertEqual(len(tt.services), 1)
        t.update(services=[{"service_id": "m1.small", "price": "23.1"}])
        db.session.commit()
        tt = Tariff.get_by_id(t.tariff_id)
        self.assertEqual(tt.services_as_dict()["m1.small"].price, Decimal("23.1"))

        t.update(services=[{"service_id": "m1.micro", "price": "231.333333"}])
        db.session.commit()
        tt = Tariff.get_by_id(t.tariff_id)
        self.assertEqual(tt.services_as_dict()["m1.micro"].price, Decimal("231.333333"))
        self.assertEqual(len(tt.services), 1)  # m1.small was removed

    def test_tariff_history(self):
        t = Tariff.create_tariff(self.localized_name("tariff_and_services"), "Test tariff with services", "RUB", None)
        user = User.query.first()
        TariffHistory.create(TariffHistory.EVENT_CREATE, user.user_id, t)
        t.update(services=[{"service_id": "m1.small", "price": "12.3456"}])
        TariffHistory.create(TariffHistory.EVENT_UPDATE, user.user_id, t)
        db.session.commit()
        self.assertEqual(TariffHistory.query.count(), 2)

        for x in range(10):
            t.update(services=[{"service_id": "m1.small", "price": "12.3456" + str(x)}])
            TariffHistory.create(TariffHistory.EVENT_UPDATE, user.user_id, t)
        db.session.commit()
        self.assertEqual(TariffHistory.query.count(), 2)


class TestTariffApi(TestCaseApi):
    def tariff_example(self, name, currency="USD"):
        tariff = {"localized_name": self.localized_name(name),
                  "description": "Very expensive tariff%s" % name,
                  "currency": currency,
                  "services": [
                      {"service_id": self.service_small_id, "price": "12.23"},
                      {"service_id": self.service_medium_id, "price": "23.45"}]}
        return tariff

    def test_create_tariff(self):
        tariff = self.tariff_example("Tariff Begin")
        tr = self.admin_client.tariff.create(as_json=True, **tariff)

        tariff_child = deepcopy(tariff)
        tariff_child["services"] = [{"service_id": "net.allocated_ip", "price": "343"}]
        tariff_child["localized_name"] = self.localized_name("Child Tariff")
        tariff_child["parent_id"] = tr["tariff_id"]
        tr_child = self.admin_client.tariff.create(as_json=True, **tariff_child)

        self.assertEqual(tr_child["localized_name"]["en"], "Child Tariff")
        self.assertEqual(tr_child["parent_id"], tr["tariff_id"])
        self.assertEqual(len(tr_child["services"]), 1)

        tariff_child2 = deepcopy(tariff_child)
        del tariff_child2["services"]
        tariff_child2["localized_name"] = self.localized_name("Child Tariff2")
        tariff_child2["parent_id"] = tr_child["tariff_id"]
        tariff_child2["currency"] = "EUR"

        with self.expect_error(errors.ParentTariffCurrency):
            self.admin_client.tariff.create(as_json=True, **tariff_child2)

        tariff_child2["currency"] = "USD"
        tr_child2 = self.admin_client.tariff.create(as_json=True, **tariff_child2)

        self.assertEqual(tr_child2["localized_name"]["en"], "Child Tariff2")
        self.assertEqual(tr_child2["parent_id"], tr_child["tariff_id"])
        self.assertEqual(len(tr_child2["services"]), 1)

        tr_child2_copy = self.admin_client.tariff.get(tr_child2["tariff_id"])
        self.maxDiff = None
        tr_child2_copy.pop("created")
        tr_child2.pop("created")
        tr_child2.pop("modified")
        tr_child2_copy.pop("modified")
        self.assertDictEqual(tr_child2_copy, tr_child2)

        # test list
        paginated_list = self.admin_client.tariff.list()["tariff_list"]
        self.assertEqual(paginated_list["total"], 3)
        self.assertEqual(len(paginated_list["items"]), 3)

        paginated_list = self.admin_client.tariff.list(description="expensive")["tariff_list"]
        self.assertEqual(paginated_list["total"], 3)

        paginated_list = self.admin_client.tariff.list(description="EXPENsive")["tariff_list"]
        self.assertEqual(paginated_list["total"], 3)

        paginated_list = self.admin_client.tariff.list(description="Unknown")["tariff_list"]
        self.assertEqual(paginated_list["total"], 0)

        paginated_list = self.admin_client.tariff.list(name="Child", description="EXPENsive")["tariff_list"]
        self.assertEqual(paginated_list["total"], 2)
        for t in paginated_list["items"]:
            self.assertEqual(len(t["localized_name"]), 2)

        paginated_list = self.admin_client.tariff.list(parent=tr_child["tariff_id"])["tariff_list"]
        self.assertEqual(paginated_list["total"], 1)

        paginated_list = self.admin_client.tariff.list(parent=tr["tariff_id"])["tariff_list"]
        self.assertEqual(paginated_list["total"], 1)
        self.assertEqual(paginated_list["items"][0]["parent_id"], tr["tariff_id"])

        paginated_list = self.admin_client.tariff.list(parent=0)["tariff_list"]
        self.assertEqual(paginated_list["total"], 1)
        self.assertEqual(paginated_list["items"][0]["parent_id"], None)

        tariff_rub = {"localized_name": self.localized_name("Rub tariff"),
                      "description": "Ruble tariff",
                      "currency": "RUB",
                      "services": [
                          {"service_id": self.service_small_id, "price": "12.23"},
                          {"service_id": self.service_medium_id, "price": "23.45"}]}
        self.admin_client.tariff.create(as_json=True, **tariff_rub)

        paginated_list = self.admin_client.tariff.list(currency="USD")["tariff_list"]
        self.assertEqual(paginated_list["total"], 3)

        paginated_list = self.admin_client.tariff.list(currency="EUR")["tariff_list"]
        self.assertEqual(paginated_list["total"], 0)

        paginated_list = self.admin_client.tariff.list(currency="RUB")["tariff_list"]
        self.assertEqual(paginated_list["total"], 1)

        self.admin_client.tariff.delete(tr_child["tariff_id"])

        paginated_list = self.admin_client.tariff.list()["tariff_list"]
        self.assertEqual(paginated_list["total"], 3)

        paginated_list = self.admin_client.tariff.list(visibility="all")["tariff_list"]
        self.assertEqual(paginated_list["total"], 4)

        paginated_list = self.admin_client.tariff.list(visibility="visible")["tariff_list"]
        self.assertEqual(paginated_list["total"], 3)

        paginated_list = self.admin_client.tariff.list(show_used=True)["tariff_list"]
        for t in paginated_list["items"]:
            self.assertEqual(t["used"], 0)

        cust = self.admin_client.customer.create(email="test@tariff.list", password="test@tariff.list")
        paginated_list = self.admin_client.tariff.list(show_used=True)["tariff_list"]
        tariff_using = {}
        for t in paginated_list["items"]:
            tariff_using[t["tariff_id"]] = t["used"]
        self.assertEqual(sorted(tariff_using.values()), [0, 0, 1])
        t = self.admin_client.tariff.create(as_json=True, **self.tariff_example('deferred tariff', 'EUR'))
        self.admin_client.tariff.immutable(t['tariff_id'])
        now_plus = utcnow().datetime + timedelta(days=2)
        self.admin_client.customer.deferred(cust['customer_id']).update(t['tariff_id'], now_plus)
        with self.expect_error(errors.RemoveUsedTariff):
            self.admin_client.tariff.delete(t['tariff_id'])

        # check filtering by creation date
        hour_ago = utcnow().replace(hours=-1).datetime
        in_hour = utcnow().replace(hours=+1).datetime

        filtered_tariffs = self.admin_client.tariff.list(created_before=in_hour)["tariff_list"]
        self.assertEqual(len(filtered_tariffs['items']), 4)

        filtered_tariffs = self.admin_client.tariff.list(created_before=hour_ago)["tariff_list"]
        self.assertEqual(len(filtered_tariffs['items']), 0)

        filtered_tariffs = self.admin_client.tariff.list(created_after=in_hour)["tariff_list"]
        self.assertEqual(len(filtered_tariffs['items']), 0)

        filtered_tariffs = self.admin_client.tariff.list(created_after=hour_ago)["tariff_list"]
        self.assertEqual(len(filtered_tariffs['items']), 4)

        filtered_tariffs = self.admin_client.tariff.list(modified_before=in_hour)["tariff_list"]
        self.assertEqual(len(filtered_tariffs['items']), 4)

        filtered_tariffs = self.admin_client.tariff.list(modified_before=hour_ago)["tariff_list"]
        self.assertEqual(len(filtered_tariffs['items']), 0)

        filtered_tariffs = self.admin_client.tariff.list(modified_after=in_hour)["tariff_list"]
        self.assertEqual(len(filtered_tariffs['items']), 0)

        filtered_tariffs = self.admin_client.tariff.list(modified_after=hour_ago)["tariff_list"]
        self.assertEqual(len(filtered_tariffs['items']), 4)

        filtered_tariffs = self.admin_client.tariff.list(visibility='deleted', deleted_before=in_hour)["tariff_list"]
        self.assertEqual(len(filtered_tariffs['items']), 1)

        filtered_tariffs = self.admin_client.tariff.list(visibility='deleted', deleted_before=hour_ago)["tariff_list"]
        self.assertEqual(len(filtered_tariffs['items']), 0)

        filtered_tariffs = self.admin_client.tariff.list(visibility='deleted', deleted_after=in_hour)["tariff_list"]
        self.assertEqual(len(filtered_tariffs['items']), 0)

        filtered_tariffs = self.admin_client.tariff.list(visibility='deleted', deleted_after=hour_ago)["tariff_list"]
        self.assertEqual(len(filtered_tariffs['items']), 1)

        with self.expect_error(errors.BadRequest):
            self.admin_client.customer.list(sort='+currency')

    def test_update_tariff(self):
        tariff = self.admin_client.tariff.create(as_json=True,
                                                 **self.tariff_example("Tariff for update"))
        new_description = "Testing description changing"
        updated_tariff = self.admin_client.tariff.update(tariff["tariff_id"], description=new_description)
        self.assertEqual(updated_tariff["description"], new_description)
        self.assertTrue(updated_tariff["mutable"])

        self.assertEqual(len(self.admin_client.tariff.history(tariff["tariff_id"])), 2)
        self.admin_client.tariff.immutable(tariff["tariff_id"])
        self.assertEqual(len(self.admin_client.tariff.history(tariff["tariff_id"])), 3)
        with self.expect_error(errors.ImmutableTariff):
            self.admin_client.tariff.update(tariff["tariff_id"], description=new_description)

        self.admin_client.tariff.make_default(tariff["tariff_id"])
        customer = self.admin_client.customer.create(email="test@tariff.list", password="test@tariff.list")

        with self.expect_error(errors.RemoveUsedTariff):
            self.admin_client.tariff.delete(tariff["tariff_id"])

        self.admin_client.customer.delete(customer["customer_id"])

        self.admin_client.tariff.delete(tariff["tariff_id"])

        self.assertEqual(len(self.admin_client.tariff.history(tariff["tariff_id"])), 4)

        now = utcnow().datetime
        now_plus = format_api_date(now + timedelta(seconds=100))
        now_minus = format_api_date(now - timedelta(seconds=100))
        history = self.admin_client.tariff.history(tariff["tariff_id"], date_after=now_plus)
        self.assertEqual(len(history), 0)

        history = self.admin_client.tariff.history(tariff["tariff_id"], date_after=now_minus)
        self.assertEqual(len(history), 4)

        history = self.admin_client.tariff.history(tariff["tariff_id"], date_before=now_minus)
        self.assertEqual(len(history), 0)

        history = self.admin_client.tariff.history(tariff["tariff_id"], date_before=now_plus)
        self.assertEqual(len(history), 4)

        history = self.admin_client.tariff.history(tariff["tariff_id"], date_before=now_plus, date_after=now_minus)
        self.assertEqual(len(history), 4)
        self.assertNotIn("snapshot", history[0])

        for history_item in history:
            hi = self.admin_client.tariff.history_item(tariff["tariff_id"], history_item["history_id"])
            self.assertIn("snapshot", hi)

    def test_update_public_flavor_service(self):
        tariff = self.admin_client.tariff.create(as_json=True,
                                                 **self.tariff_example("Tariff for update"))
        self.admin_client.tariff.immutable(tariff["tariff_id"])

        tariff = Tariff.get_by_id(tariff["tariff_id"])
        tariff.services.append(ServicePrice(self.service_nano_id, 0, True))

        db.session.commit()

        updated = self.admin_client.tariff.update(
            resource_id=tariff.tariff_id,
            as_json=True,
            services=[
                {"service_id": str(self.service_nano_id), "price": "11.11"},
                {"service_id": str(self.service_medium_id), "price": "100"}
            ]
        )

        db.session.add(tariff)

        self.assertEqual(tariff.services_as_dict()[str(self.service_nano_id)].need_changing, False)
        self.assertEqual(tariff.services_as_dict()[str(self.service_nano_id)].price, Decimal('11.11'))
        self.assertEqual(tariff.services_as_dict()[str(self.service_medium_id)].price, Decimal('23.45'))

    def test_force_delete_tariff(self):
        tariff = self.admin_client.tariff.create(as_json=True, **self.tariff_example("$test_tariff"))
        self.admin_client.tariff.immutable(tariff["tariff_id"])
        self.admin_client.tariff.make_default(tariff["tariff_id"])

        new_tariff = self.admin_client.tariff.create(as_json=True, **self.tariff_example("tttt"))
        self.admin_client.tariff.immutable(new_tariff["tariff_id"])

        deleted = self.admin_client.delete("/api/0/_force_delete/",
                                           {"prefix": "$test", "tables": "tariff"}).json["deleted"]
        self.assertEqual(deleted["tariff"], 0)

        self.admin_client.tariff.make_default(new_tariff["tariff_id"])
        deleted = self.admin_client.delete("/api/0/_force_delete/",
                                           {"prefix": "$test", "tables": "tariff"}).json["deleted"]
        self.assertEqual(deleted["tariff"], 1)

    def test_tariff_default(self):
        tariff = self.admin_client.tariff.create(as_json=True, **self.tariff_example("default_tariff"))
        with self.expect_error(errors.MutableTariffCantBeDefault):
            self.admin_client.tariff.make_default(tariff["tariff_id"])
        self.admin_client.tariff.immutable(tariff["tariff_id"])
        self.admin_client.tariff.make_default(tariff["tariff_id"])
        db.session.rollback()  # verify that changes were committed

        tariff = self.admin_client.tariff.get(tariff["tariff_id"])
        for s in tariff["services"]:
            self.assertRegex(s["price"], r"\d+\.\d\d")
        self.assertTrue(tariff["default"])

        new_tariff = self.admin_client.tariff.create(as_json=True, **self.tariff_example("new_tariff"))
        self.admin_client.tariff.immutable(new_tariff["tariff_id"])
        self.admin_client.tariff.make_default(new_tariff["tariff_id"])
        new_tariff = self.admin_client.tariff.get(new_tariff["tariff_id"])
        self.assertTrue(new_tariff["default"])
        old_tariff = self.admin_client.tariff.get(tariff["tariff_id"])
        self.assertFalse(old_tariff["default"])

        default_tariff = self.admin_client.tariff.get_default()
        self.assertEqual(default_tariff["tariff_id"], new_tariff["tariff_id"])
