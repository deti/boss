from sqlalchemy import Column, ForeignKey

from model import db, AccountDb


class CustomerInfo(AccountDb):
    _mandatory_production_fields = []

    def validate_production_fields(self):
        for field in self._mandatory_production_fields:
            if not getattr(self, field):
                return False
        return True

    @classmethod
    def create(cls, customer_id, info_parameters):
        customer_info = cls()
        customer_info.customer_id = customer_id
        for field, value in info_parameters.items():
            if hasattr(cls, field):
                setattr(customer_info, field, value)
        db.session.add(customer_info)
        db.session.flush()
        return customer_info

    def update(self, new_parameters):
        new_parameters = {k: v for k, v in new_parameters.items() if hasattr(self, k)}
        res = super().update(new_parameters)
        return res


class PrivateCustomerInfo(CustomerInfo, db.Model):
    id_field = "info_id"

    info_id = Column(db.Integer, primary_key=True)
    name = Column(db.String(64))
    birthday = Column(db.Date())
    country = Column(db.String(32))
    city = Column(db.String(32))
    address = Column(db.String(254))
    passport_series_number = Column(db.String(16))
    passport_issued_by = Column(db.String(254))
    passport_issued_date = Column(db.Date())
    telephone = Column(db.String(16))
    customer_id = Column(db.Integer, ForeignKey("customer.customer_id", ondelete="CASCADE"), index=True)

    _mandatory_production_fields = []

    display_fields = frozenset(['name', 'birthday', 'passport_series_number', 'passport_issued_by',
                                'passport_issued_date', 'telephone', 'address', 'city', 'country'])

    def __str__(self):
        return "<PrivateCustomerInfo %s name:%s, address: %s>" % (self.customer_id, self.name, self.address)


class EntityCustomerInfo(CustomerInfo, db.Model):
    id_field = "info_id"

    info_id = Column(db.Integer, primary_key=True)
    contract_number = Column(db.String(64))
    contract_date = Column(db.Date())
    name = Column(db.String(64))
    full_organization_name = Column(db.String(254))
    primary_state_registration_number = Column(db.String(16))
    individual_tax_number = Column(db.String(16))
    legal_address_country = Column(db.String(32))
    legal_address_city = Column(db.String(32))
    legal_address_address = Column(db.String(254))
    location_country = Column(db.String(32))
    location_city = Column(db.String(32))
    location_address = Column(db.String(254))
    general_manager_name = Column(db.String(254))
    general_accountant_name = Column(db.String(254))
    contact_person_name = Column(db.String(254))
    contact_person_position = Column(db.String(64))
    contact_telephone = Column(db.String(16))
    contact_email = Column(db.String(254))
    customer_id = Column(db.Integer, ForeignKey("customer.customer_id", ondelete="CASCADE"), index=True)

    _mandatory_production_fields = ['contract_number', 'contract_date', 'name',
                                    'full_organization_name', 'primary_state_registration_number',
                                    'individual_tax_number', 'legal_address_country', 'legal_address_city',
                                    'legal_address_address', 'location_country', 'location_city', 'location_address',
                                    'general_manager_name', 'general_accountant_name'
                                    ]

    display_fields = frozenset(['contract_number', 'contract_date', 'name',
                                'full_organization_name', 'primary_state_registration_number',
                                'individual_tax_number', 'legal_address_country', 'legal_address_city',
                                'legal_address_address', 'location_country', 'location_city', 'location_address',
                                'general_manager_name', 'general_accountant_name', 'contact_person_name',
                                'contact_person_position', 'contact_telephone', 'contact_email'])

    def __str__(self):
        return "<EntityCustomerInfo customer_id=%s>" % self.customer_id
