"""
Module for all entities generators. Used to generate stub information for api methods calls.
"""

import datetime
import configs
from utils.tools import format_backend_date


class Entity(object):
    """
    shema is a basic part of entity info. It is used in main generate method and can be overriden by kwargs.
    """
    shema = None

    def __init__(self, test_case):
        """
        :param utils.base.BaseTestCase test_case: basetestcase
        """
        self.test_case = test_case

    def get_shema(self) -> dict:
        """
        Return basic shema.

        :return dict: shema
        """
        if self.shema is None:
            raise NotImplementedError
        return self.shema.copy()

    def generate(self, *args, **kwargs) -> dict:
        """
        Main method for generating entity info. Call it with some kwargs to override basic shema.

        :param dict kwargs: used to override shema info.
        :return dict: generated shema
        """
        shema = self.get_shema()
        shema.update(kwargs)
        return shema

    def generate_password(self) -> str:
        """Shortcut function to generate common password"""
        return self.test_case.generate_password()

    def generate_email(self, domain: str='example.com') -> str:
        """Shortcut function to generate common email"""
        return self.test_case.generate_email(domain)

    def basic_name(self, name: str=None) -> str:
        """Shortcut function to generate common name"""
        return self.test_case.create_name(name)

    def localized_name(self, ru: bool=True) -> dict:
        """Create a localized name dict"""
        localized = {'en': self.basic_name()}
        if ru:
            localized['ru'] = self.basic_name('ру')
        return localized


class LocalizedNameEntity(Entity):
    def get_shema(self):
        return {
            'localized_name': self.localized_name()
        }


class Service(LocalizedNameEntity):
    default_measure_id = 'hour'

    def get_shema(self) -> dict:
        shema = super().get_shema()
        shema.update({
            'measure': self.default_measure_id,
            'description': self.localized_name()
        })
        return shema


class Tariff(LocalizedNameEntity):
    default_currency = 'RUB'

    def get_shema(self) -> dict:
        shema = super().get_shema()
        shema.update({
            'currency': self.default_currency,
            'description': self.basic_name()
        })
        return shema


class News(Entity):
    def get_shema(self):
        return {
            'subject': self.basic_name(),
            'body': self.basic_name()
        }


class CredentialsEntity(Entity):
    def get_shema(self):
        return {
            'email': self.generate_email(),
            'password': self.generate_password(),
            'name': self.basic_name()
        }


class AdminCredentials(CredentialsEntity):
    default_role = 'admin'

    def get_shema(self) -> dict:
        shema = super().get_shema()
        shema.update({
            'role': self.default_role
        })
        return shema


class CustomerCredentials(Entity):
    default_birthday = format_backend_date(datetime.date(1994, 6, 14))
    default_country = 'Russia'
    default_city = 'Orenburg'
    default_address = 'Saint Van Rossum street 3/4'
    default_phone = '+71234567890'

    def generate_detailed_info(self) -> dict:
        return {
            'name': self.basic_name(),
            'birthday': self.default_birthday,
            'country': self.default_country,
            'city': self.default_city,
            'address': self.default_address,
            'telephone': self.default_phone
        }

    def generate_individual_fields(self):
        return {
            "passport_series_number": '1234567890123',
            "passport_issued_by": self.default_address,
            "passport_issued_date": self.default_birthday,
        }

    def generate_entity_fields(self):
        return {
            "contract_number": "2015/4568",
            "contract_date": "2015-01-01",
            "organization_type": "OOO",
            "full_organization_name": "OOO Рога и копыта",
            "primary_state_registration_number": "159 8525 15552",
            "individual_tax_number": "52 59 5555555",
            "legal_address_country": self.default_country,
            "legal_address_city": self.default_city,
            "legal_address_address": self.default_address,
            "location_country": self.default_country,
            "location_city": self.default_city,
            "location_address": self.default_address,
            "general_manager_name": "Джейсон Стетхем",
            "general_accountant_name": "Кларк Кент",
            "contact_person_name": "Брюс Уейн"
        }

    def get_shema(self) -> dict:
        shema = {
            'email': self.generate_email(),
            'password': self.generate_password(),
            'detailed_info': self.generate_detailed_info()
        }
        return shema

    def generate(self, individual:bool=False, entity:bool=False,
                 with_promocode:bool=configs.promocodes.promo_registration_only, **kwargs):
        credentials = super().generate(**kwargs)
        if with_promocode:
            credentials['promo_code'] = self.test_case.get_default_promocode()
        if individual:
            credentials['detailed_info'].update(self.generate_individual_fields())
        elif entity:
            credentials['detailed_info'].update(self.generate_entity_fields())
        return credentials
