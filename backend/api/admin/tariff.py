import conf
import errors
from model import display, autocommit
from api import get, post, delete, put, AdminApi
from api.check_params import check_params
from api.validator import IntRange, String, TokenId, List, ModelId, Visibility, LocalizedName, JSONList, Bool, Date, \
    SortFields
from api.admin.role import TokenAccount
from model import Tariff, Service, TariffLocalization, TariffHistory
from api.admin.currency import ActiveCurrencies
from utils.money import string_to_decimal


TariffIdExpand = ModelId(Tariff, errors.TariffNotFound)
TariffId = ModelId(Tariff, errors.TariffNotFound, expand=False)
_sentinel = object()

class Price(String):
    def __call__(self, value):
        value = super().__call__(value)
        return string_to_decimal(value)


class ServicePriceListValidator(JSONList):
    def __init__(self):
        super().__init__({"service_id": String(), "price": Price()})

    def __call__(self, value):
        service_price_list = super().__call__(value)
        for service_price in service_price_list:
            service_id = service_price.get("service_id")
            service = Service.get_by_id(service_id)
            if not service:
                raise errors.ServiceNotFound()
            if service.deleted:
                raise errors.RemovedServiceInTariff()
            if service.mutable:
                raise errors.OnlyImmutableService()

        return service_price_list


class TariffApi(AdminApi):
    @get('tariff/<tariff>/')
    @check_params(
        token=TokenId,
        tariff=TariffIdExpand
    )
    def fetch_tariff(self, tariff):
        """
        Returns tariff info

        :param ID tariff: Tariff ID
        :return dict tariff_info: Returns dict with tariff description.

        **Example**::

              "tariff_info": {
                "services": [
                  {
                    "price": "12.23",
                    "default": false,
                    "service": {
                      "service_id": "m1.small",
                      "category": {
                        "category_id": "vm",
                        "localized_name": {
                          "ru": "\u0412\u0438\u0440\u0442\u0443\u0430\u043b\u044c\u043d\u044b\u0435 \u043c\u0430\u0448\u0438\u043d\u044b",
                          "en": "Virtual machine"
                        }
                      },
                      "measure": {
                        "localized_name": {
                          "ru": "\u0447\u0430\u0441",
                          "en": "hour"
                        },
                        "measure_id": "hour",
                        "measure_type": "time"
                      },
                      "localized_name": {
                        "en": "m1.small",
                        "ru": "m1.small"
                      }
                    }
                  },
                  {
                    "price": "23.45",
                    "service": {
                      "service_id": "m1.medium",
                      "category": {
                        "category_id": "vm",
                        "localized_name": {
                          "ru": "\u0412\u0438\u0440\u0442\u0443\u0430\u043b\u044c\u043d\u044b\u0435 \u043c\u0430\u0448\u0438\u043d\u044b",
                          "en": "Virtual machine"
                        }
                      },
                      "measure": {
                        "localized_name": {
                          "ru": "\u0447\u0430\u0441",
                          "en": "hour"
                        },
                        "measure_id": "hour",
                        "measure_type": "time"
                      },
                      "localized_name": {
                        "en": "m1.medium",
                        "ru": "m1.medium"
                      }
                    }
                  }
                ],
                "deleted": null,
                "parent_id": null,
                "localized_name": {
                  "en": "Tariff Begin",
                  "ru": "\u0422\u0430\u0440\u0438\u0444\u0444 \u0411\u0435\u0433\u0438\u043d"
                },
                "created": "2015-05-26T18:09:02+00:00",
                "description": "\u0416\u0443\u0442\u043a\u043e \u0434\u043e\u0440\u043e\u0433\u043e\u0439 \u0442\u0430\u0440\u0438\u0444\u0444",
                "tariff_id": 1,
                "mutable": true,
                "currency": "rub"
              }
            }
        """
        # , expand_references_in_list=Tariff.expand_references_in_list
        return {"tariff_info": display(tariff)}

    @get('tariff/')
    @check_params(
        token=TokenId,
        name=String,
        description=String,
        currency=ActiveCurrencies,
        deleted_before=Date(), deleted_after=Date(),
        created_before=Date(), created_after=Date(),
        modified_before=Date(), modified_after=Date(),
        visibility=Visibility,
        parent=ModelId,
        page=IntRange(1),
        limit=IntRange(1, conf.api.pagination.limit),
        sort=List(SortFields(Tariff)),  # Sort(Tariff.Meta.sort_fields),
        show_used=Bool,
        all_parameters=True
    )
    def fetch_list(self, all_parameters, name=None, description=None, currency=None,
                   deleted_before=None, deleted_after=None,
                   created_before=None, created_after=None,
                   modified_before=None, modified_after=None,
                   parent=_sentinel, visibility=Visibility.DEFAULT,
                   page=1, limit=conf.api.pagination.limit,
                   sort=None, show_used=False):
        """
        Returns paginated filtered tariff list.

        :param str name: Match tariff name
        :param str description: Match tariff description
        :param str currency: Match by currency
        :param TariffId parent: Match by parent tariff

            The following values are possible:

            - Valid tariff id: Returns list of children tariffs;
            - 0: Returns list of tariffs without parents.

        :param str visibility:
            The following values are possible:
            - visible: returns all not archived tariffs
            - deleted: returns only archived tariffs
            - all: returns all tariffs

            By default "visible" is used

        :param int page: Page
        :param int limit: Numbers of items per page.
        :param bool show_used: include field "used" in the reply which means how many customers are assigned
                                 to this tariff
        :param str or List sort: Sorting field name.
                                 Ascending ordering is default.
                                 For descending ordering use "-" before.

        :return list tariff_list: List of tariff info dictionaries (dict as in :obj:`GET /0/tariff/\<tariff\>/ <view.GET /0/tariff/\<tariff\>>`)

        **Example**::

                {
                    "tariff_list": {
                       "items": [
                            {
                                ...
                            },
                            {
                                ...
                            }
                       ]
                       "total": 2,
                       "limit": 200,
                       "offset": 0
                    }
                }
        """
        all_parameters.pop("show_used", None)
        query = Tariff.query
        extract_by_id = False
        if parent is not _sentinel:
            if parent:
                query = query.filter_by(parent_id=parent)
            else:
                query = query.filter_by(parent_id=None)
        if name:
            query = query.join(Tariff.localized_name).\
                filter(TariffLocalization.localized_name.ilike("%{}%".format(name)))
            extract_by_id = True

        # noinspection PyUnresolvedReferences
        all_parameters.setdefault("limit", limit)
        # noinspection PyUnresolvedReferences
        all_parameters.setdefault("page", page)
        query = Tariff.api_filter(all_parameters, exact={"currency"}, query=query, extract_by_id=extract_by_id,
                                  visibility=visibility)
        short_display = [] if show_used else False
        return {"tariff_list": self.paginated_list(query, short_display=short_display)}

    @post("tariff/")
    @check_params(
        token=TokenAccount,
        localized_name=LocalizedName,
        description=String,
        currency=ActiveCurrencies,
        parent_id=TariffId,
        services=ServicePriceListValidator,
        all_parameters=True
    )
    @autocommit
    def new_tariff(self, token, localized_name, description, currency,
                   services=None, parent_id=None, all_parameters=None):
        """
        Create new tariff.

        Parameters must be sent as json object.

        :param LocalizedName localized_name: Dict with name localization. en is mandatory key
                ``{"en": "Name", "ru": "\u0418\u043c\u044f"}``
        :param str description: Tariff description
        :param str currency: Currency code
        :param TariffId parent_id: Parent tariff id
        :param list services: List services and its prices

            **Example of list**::

                    services: [
                        {
                            "service_id": "m1.small",
                            "price": "12.23"
                        },
                        {
                            "service_id": "m1.medium",
                            "price": "21.32"
                        }
                    ]
                }

        :return dict tariff_info: Dict as returned by :obj:`GET /0/tariff/\<tariff\>/ <view.GET /0/tariff/\<tariff\>>`
        """
        if parent_id:
            parent = Tariff.get_by_id(parent_id)
            if not parent:
                raise errors.TariffNotFound()
            if parent.currency != currency:
                raise errors.ParentTariffCurrency()

        created = Tariff.create_tariff(**all_parameters)
        TariffHistory.create(TariffHistory.EVENT_CREATE, token.user_id, created)
        return {"tariff_info": display(created)}

    # noinspection PyUnusedLocal
    @put('tariff/<tariff>/')
    @check_params(
        token=TokenAccount,
        tariff=TariffIdExpand,
        localized_name=LocalizedName,
        description=String,
        currency=ActiveCurrencies,
        services=ServicePriceListValidator,
        all_parameters=True,
    )
    @autocommit
    def update_tariff(self, token, tariff, localized_name=None, description=None,
                      currency=None, services=None, all_parameters=None):
        """
        Update tariff.

        Parameters must be sent as json object.

        :param Id tariff: Tariff Id.
        :param LocalizedName localized_name: Dict with name localization. en is mandatory key
                ``{"en": "Name", "ru": "\u0418\u043c\u044f"}``
        :param str description: Tariff description.
        :param str currency: Currency.
        :param list services: List services and its prices

        :return dict tariff_info: Dict as returned by :obj:`GET /0/tariff/\<tariff\>/ <view.GET /0/tariff/\<tariff\>>`
        """
        all_parameters.pop("tariff")
        updated = tariff.update(**all_parameters)
        if updated:
            TariffHistory.create(TariffHistory.EVENT_UPDATE, token.user_id, tariff)

        return {"tariff_info": display(tariff)}

    @delete('tariff/<tariff>/')
    @check_params(
        token=TokenAccount,
        tariff=TariffIdExpand
    )
    @autocommit
    def archive_tariff(self, token, tariff):
        """
        Move the tariff to archive.

        .. note::
            Only unused tariffs can be archived.

        :param Id tariff: Tariff ID.

        :return: Empty object
        """
        if tariff.remove():
            TariffHistory.create(TariffHistory.EVENT_DELETE, token.user_id, tariff)
        return {}

    @put('tariff/<tariff>/immutable/')
    @check_params(
        token=TokenAccount,
        tariff=TariffIdExpand,
    )
    @autocommit
    def immutable(self, token, tariff):
        """
        Update tariff.

        :param Id tariff: Tariff Id.
        :return dict tariff_info: Dict as returned by :obj:`GET /0/tariff/\<tariff\>/ <view.GET /0/tariff/\<tariff\>>`
        """
        if tariff.mark_immutable():
            TariffHistory.create(TariffHistory.EVENT_IMMUTABLE, token.user_id, tariff)

        return {"tariff_info": display(tariff)}

    @get('tariff/<tariff>/history/')
    @check_params(
        token=TokenId,
        tariff=TariffIdExpand,
        date_before=Date(),
        date_after=Date(),

    )
    def fetch_tariff_history_list(self, tariff, date_before=None, date_after=None):
        """
        Returns list of changes for tariff

        :param ID tariff: Tariff ID
        :param Date date_before: Returns events which were happened before this date
        :param Date date_after: Returns events which were happened after this date

        :return List tariff_history_list: tariff operations list.

        """

        return {"tariff_history": display(tariff.get_history(date_before, date_after), short=True)}

    @get('tariff/<tariff>/history/<history>/')
    @check_params(
        token=TokenId,
        tariff=TariffIdExpand,
        history=ModelId,
        date_before=Date(),
        date_after=Date(),

    )
    def fetch_tariff_history_item(self, tariff, history):
        """
        Returns list of changes for tariff

        :param ID tariff: Tariff ID

        :return List tariff_history_list: Changes list for the tariff

        """
        history = tariff.history.filter(TariffHistory.history_id == history).first()
        if not history:
            raise errors.TariffHistoryNotFound()

        return {"tariff_history_info": display(history, short=False)}

    @put('tariff/<tariff>/default/')
    @check_params(
        token=TokenAccount,
        tariff=TariffIdExpand,
    )
    @autocommit
    def make_default(self, tariff):
        """
        Make tariff default

        :param ID tariff: Tariff ID

        :return dict tariff_info: Returns dict with tariff description.

        """
        tariff.make_default()
        return {"tariff_info": display(tariff)}

    @get('tariff/default/')
    @check_params(
        token=TokenId,
    )
    def get_default(self):
        """
        Get description of default tariff

        :return dict tariff_info: Returns dict with tariff description.

        """
        tariff = Tariff.get_default().first()
        if not tariff:
            raise errors.TariffNotFound()
        return {"tariff_info": display(tariff)}
