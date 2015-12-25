import conf
import arrow
import logbook
import warnings
from collections.abc import Iterable
from sqlalchemy.exc import IntegrityError
from model.sa import SQLAlchemy
from attrdict import AttrDict
from functools import wraps
from sqlalchemy.orm import joinedload


warnings.filterwarnings("ignore", "Data truncated for column")


def database_config():
    config = AttrDict(conf.database.copy())
    test = config.pop("test")
    if conf.test:
        for k, v in test.items():
            config[k] = v
    return config

db = SQLAlchemy(database_config())


class DisplayedModel:
    display_fields = None
    display_fields_short = None
    expand_fields = frozenset()
    extract_fields = {}
    sorting_fields = None

    def display(self, short=True):
        fields = self.display_fields_short or self.display_fields if short else self.display_fields

        def get_value(field):
            value = getattr(self, field)
            if field in self.expand_fields:
                value = display(value)
            elif field in self.extract_fields:
                value = self.extract_fields[field](value)
            return value

        return {f: get_value(f) for f in fields}

    def __repr__(self):
        return str(self)


class BaseModel(DisplayedModel):
    id_field = None
    unique_field = None

    @classmethod
    def get_by_id(cls, model_id):
        return cls.query.get(model_id)

    @classmethod
    def filter_by_id(cls, model_id):
        assert cls.id_field
        return cls.query.filter_by(**{cls.id_field: model_id})

    def mark_removed(self):
        if self.deleted:
            return False
        self.deleted = arrow.utcnow().datetime
        return True

    @classmethod
    def sort_query(cls, query, sort):
        fields = []
        for field in sort:
            if field.startswith('-'):
                field = getattr(cls, field[1:]).desc()
            else:
                field = getattr(cls, field)

            fields.append(field)

        query = query.order_by(*fields)

        return query

    @classmethod
    def api_filter(cls, query_parameters, exact=None, query=None, extract_by_id=False, visibility=None):
        limit = query_parameters.pop("limit")
        page = query_parameters.pop("page")
        sort = query_parameters.pop("sort", None)
        if query is None:
            query = cls.query

        if visibility:
            query_parameters.pop("visibility", None)
            if visibility == "all":
                pass
            elif visibility == "visible":
                query = query.filter(cls.deleted == None)
            elif visibility == "deleted":
                query = query.filter(cls.deleted != None)

        for k, v in query_parameters.items():
            if k in cls.__table__.columns:
                if k in (exact or {}):
                    query = query.filter_by(**{k: v})
                elif v is not None:
                    column = cls.__table__.columns[k]
                    query = query.filter(column.ilike("%{}%".format(v)))
            elif k.endswith('_before'):
                query = query.filter(getattr(cls, k.partition('_before')[0]) < v)
            elif k.endswith('_after'):
                query = query.filter(getattr(cls, k.partition('_after')[0]) > v)

        if extract_by_id:
            subquery = query.with_entities(cls.id_field).subquery()
            query = cls.query.filter(cls.__table__.columns[cls.id_field].in_(subquery)).\
                options(joinedload('localized_name'))

        if sort:
            query = cls.sort_query(query, sort)

        return query.paginate(page, limit)

    @classmethod
    def delete_by_prefix(cls, prefix, field=None):
        field = field or cls.unique_field
        if not field:
            raise Exception("Field for removing is not set")
        member = getattr(cls, field)
        return cls.query.filter(member.like(prefix + "%")).delete(False)

    def update(self, parameters):
        logbook.debug("Update {} with parameters: {}", self, parameters)
        for key, value in parameters.items():
            assert key in self.__table__.columns
            setattr(self, key, value)

    def __str__(self):
        # noinspection PyUnresolvedReferences
        try:
            fields = self.__table__.columns.keys()
            columns = ", ".join("%s=%s" % (k, self.__dict__.get(k, "<Unknown field %s>" % k)) for k in fields)
            return "<%s %s>" % (self.__class__.__name__, columns)
        except Exception as e:
            logbook.error("__str__ failed for {}: {}", type(self), e)
            return str(type(self))

    def to_dict(self):
        result = {}
        for key in self.__mapper__.c.keys():
            result[key] = getattr(self, key)
        return result


class AccountDb(BaseModel):
    pass


class FitterDb(BaseModel):
    __bind_key__ = 'fitter'


def duplicate_handle(duplicate_exception):
    def outer(fn):
        @wraps(fn)
        def inner(*args, **kwargs):
            try:
                res = fn(*args, **kwargs)
                db.session.flush()
                return res
            except IntegrityError as e:
                # after exception all model were became expired. To represent object as string,
                # new request to db is needed to refresh object.
                # But this is impossible because of previous sql command was failed.
                # So we should exclude any model from debug output.
                args = tuple(value for value in args if not isinstance(value, db.Model))
                logbook.debug("Integrity error for {}({}, {}): {}", fn.__qualname__, args, kwargs, e)
                raise duplicate_exception()
        return inner
    return outer


def autocommit(fn):
    import errors

    @wraps(fn)
    def wrap(*args, **kwargs):
        try:
            res = fn(*args, **kwargs)
            db.session.commit()
            return res
        except errors.BadRequest:
            db.session.rollback()
            raise
        except Exception:
            logbook.exception("Exception in function {}:", fn)
            db.session.rollback()
            raise

    return wrap


def display(value, short=False, expand_references_in_list=None):
    if value is None:
        return value
    if hasattr(value, "display"):
        result = value.display(short)
        if expand_references_in_list is not None:
            expand_references_in_list([result])
        return result
    if isinstance(value, str):
        return value
    if isinstance(value, Iterable):
        result = [display(l, short) for l in value]
        if expand_references_in_list is not None:
            expand_references_in_list(result)
        return result
    raise Exception("Incorrect type for display %s (%s)" % (value, type(value)))

from model.account.message_template import MessageTemplate
from model.account.scheduled_task import ScheduledTask
from model.account.customer import Customer, Subscription, SubscriptionSwitch, Quote, CustomerCard, PromoCode
from model.account.customer_info import PrivateCustomerInfo, EntityCustomerInfo
from model.account.user import User
from model.account.service import FixedService, Measure, Category, Service, ServiceLocalization, ServiceDescription,\
    Flavor
from model.account.tariff import TariffLocalization, Tariff, TariffHistory, ServicePrice
from model.account.news import News
from model.fitter.service_usage import ServiceUsage
from model.account.tenant import Tenant
from model.account.deferred import Deferred
from model.account.account import Account, AccountHistory
from model.account.customer_history import CustomerHistory
from model.account.option import Option
from model.account.time_state import TimeState, TimeMachine
