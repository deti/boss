# -*- coding: utf-8 -*-
from utils.bootstrap import BootstraperBase
from model import User, db, Service


class BootstrapTest(BootstraperBase):
    def process_doc(self, filename):
        super().process_doc(filename)
        db.session.commit()

    def create_user(self, params=None):
        return User.new_user(**params)

    def create_tariff(self, params=None):
        pass

    def create_customer(self, params=None):
        pass

    def create_flavor(self, params=None):
        service = Service.create_vm(**params)
        service.mark_immutable()
        return service
