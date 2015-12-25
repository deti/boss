import metayaml
from abc import ABCMeta, abstractmethod


class BootstraperBase(metaclass=ABCMeta):
    def process_doc(self, filename):
        doc = self.read_config(filename)
        creation_order = ["user", "service", "flavor", "tariff", "customer", "news", "tenant"]
        for entity in creation_order:
            entries = doc.get(entity)
            if not entries:
                continue
            factory = getattr(self, "create_{}".format(entity), None)
            if not factory:
                raise Exception("Don't know how to create {}".format(entity))
            for entry in entries:
                factory(entry)

    def fill_defaults(self):
        pass

    @abstractmethod
    def create_tariff(self, params=None):
        pass

    @abstractmethod
    def create_user(self, params=None):
        pass

    @abstractmethod
    def create_customer(self, params=None):
        pass

    @staticmethod
    def read_config(filename):
        return metayaml.read(filename)
