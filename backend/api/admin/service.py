import conf
import errors
from model import display, autocommit
from api import get, post, delete, AdminApi, put
from api.check_params import check_params
from api.validator import IntRange, String, TokenId, List, Choose, LocalizedName, ModelId, Visibility, Integer
from api.admin.role import TokenAdmin, TokenAccount, TokenManager
from model import Category, Service, Measure
from os_interfaces.openstack_wrapper import openstack
from novaclient.exceptions import NotFound

CategoryList = List(Choose(list(Category.list().keys())))
MeasureTime = Choose({measure.measure_id: measure for measure in Measure.list(Measure.TIME)})
ServiceIdExpand = ModelId(Service, errors.ServiceNotFound)
ServiceId = ModelId(Service, errors.ServiceNotFound, expand=False)


class ServiceApi(AdminApi):
    @get("category/")
    @check_params(
        token=TokenId,
    )
    def service_category_list(self):
        """
        Returns list of categories with localized names

        :return list category_list: List of dict with category

        **Example**::

             {"category_list": [
                {"category_id": "net", "localized_name": {"ru": "Сеть", "en": "Network"}},
                {"category_id": "storage", "localized_name": {"ru": "Хранение данных", "en": "Storage"}},
                {"category_id": "vm", "localized_name": {"ru": "Виртуальные машины", "en": "Virtual machine"}},
                {"category_id": "custom", "localized_name": {"ru": "Дополнительные", "en": "Custom"}}]}

        """
        return {"category_list": display(Category.list().values())}

    @get("measure/")
    @check_params(
        token=TokenId,
        measure_type=Choose(Measure.TYPES)
    )
    def measure_list(self, measure_type=None):
        """
        Returns list of measures

        :param String measure_type: Return measures only specified type. It can be "time", "quant" or 'time_quant'
        :return list measure_list: List of dict with measure info

        **Example**::

            {
                "measure_list": [
                   {"measure_type": "time", "localized_name": {"ru": "час", "en": "hour"}, "measure_id": "hour"},
                   {"measure_type": "time", "localized_name": {"ru": "месяц", "en": "month"}, "measure_id": "month"}
                ]
            }
        """
        return {"measure_list": display(Measure.list(measure_type))}

    @post("service/custom/")
    @check_params(
        token=TokenAccount,
        localized_name=LocalizedName,
        description=LocalizedName(requires_default_language=False),
        measure=MeasureTime
    )
    @autocommit
    def new_custom_service(self, localized_name, measure, description=None):
        """
        Add new custom service.

        Parameters must be sent as json object.

        :param LocalizedName localized_name: Dict with name localization. en is mandatory key
                ``{"en": "Name", "ru": "\u0418\u043c\u044f"}``
        :param LocalizedName description: Dict with localized description. (Not mandatory)
        :param Measure measure: Measure id. Only time measure is possible.

        **Example**::

            {"service_info":
                {
                    "mutable": true,
                    "localized_name": {
                        "ru": "",
                        "en": "Test Custom Service"
                    },
                    "deleted": null,
                    "measure": {
                        "localized_name": {
                            "ru": "\u0447\u0430\u0441",
                            "en": "hour"
                        },
                        "measure_type": "time",
                        "measure_id": "hour"
                    },
                    "category": {
                        'localized_name':
                            {'ru': 'Дополнительные', 'en': 'Custom'},
                            'category_id': 'custom'
                        },
                    "service_id": 1,
                    "description": {}
                }
            }

        """
        service = Service.create_custom(localized_name, measure, description)
        return {"service_info": display(service)}

    @staticmethod
    def check_flavor_existence(flavor_info):
        try:
            flavor = openstack.get_nova_flavor(flavor_info['flavor_id'])
            if (flavor_info['vcpus'], flavor_info['ram'], flavor_info['disk']) != \
                    (flavor.vcpus, flavor.ram, flavor.disk):
                raise errors.OsFlavorExistsWithDifferentParams(
                    "Flavor already exists in OS with different parameters: vcpus: %s, ram: %s, disk: %s" % \
                    (flavor.vcpus, flavor.ram, flavor.disk)
                )
        except NotFound:
            return False

        return True

    @post("service/vm/")
    @check_params(
        token=TokenManager,
        flavor_id=String(),
        vcpus=Integer(),
        ram=Integer(),
        disk=Integer(),
        network=Integer(),
        localized_name=LocalizedName,
        description=LocalizedName(requires_default_language=False)
    )
    @autocommit
    def new_vm(self, flavor_id, vcpus, ram, disk, localized_name, network=None, description=None):
        """
        Add new flavor service.

        Parameters must be sent as json object.

        :param LocalizedName localized_name: Dict with name localization. en is mandatory key
                ``{"en": "Name", "ru": "\u0418\u043c\u044f"}``
        :param LocalizedName description: Dict with localized description. (Not mandatory)
        :param flavor_id: Flavor name
        :param vcpus: Number of flavor's vcpus
        :param ram: flavor's RAM amount
        :param disk: flavor's disk size
        :param network: flavor's network

        **Example**::

            {"service_info":
                {
                    "mutable": true,
                    "localized_name": {
                        "ru": "\u0424\u043b\u0430\u0432\u043e\u0440 TestFlavor",
                        "en": "Flavor TestFlavor"
                    },
                    "deleted": null,
                    "measure": {
                        "localized_name": {
                            "ru": "\u0447\u0430\u0441",
                            "en": "hour"
                        },
                        "measure_type": "time",
                        "measure_id": "hour"
                    },
                    "category": {
                        "localized_name": {
                            "ru": "\u0412\u0438\u0440\u0442\u0443\u0430\u043b\u044c\u043d\u044b\u0435 \u043c\u0430\u0448\u0438\u043d\u044b",
                            "en": "Virtual server"
                        },
                        "category_id": "vm"
                    },
                    "service_id": 1,
                    "description": {}
                }
            }

        """
        flavor_info = dict(flavor_id=flavor_id, vcpus=vcpus, ram=ram, disk=disk, network=network)
        mutable = True
        if self.check_flavor_existence(flavor_info):
            mutable = False
        flavor = Service.create_vm(localized_name, description, flavor_info, mutable)
        return {"service_info": display(flavor)}

    @get('service/<service_id>/')
    @check_params(
        token=TokenId,
        service_id=String)
    def get_service(self, service_id):
        """
        Return service description

        :param Id service_id: Service Id

        :return dict service_info: Dict with service parameters

        **Example**::

            {
              "service_info": {
                "service_id": "storage.volume",
                "measure": {
                  "measure_type": "time_quant",
                  "measure_id": "gigabyte*month",
                  "localized_name": {
                    "ru": "Гб*месяц",
                    "en": "Gb*month"
                  }
                },
                "category": {
                  "localized_name": {
                    "ru": "Хранение данных",
                    "en": "Storage"
                  },
                  "category_id": "storage"
                },
                "localized_name": {
                  "ru": "Диск",
                  "en": "Volume"
                }
              }
            }

        """

        service = Service.get_by_id(service_id)
        if not service:
            raise errors.ServiceNotFound()

        return {"service_info": display(service)}

    @delete('service/<service>/')
    @check_params(token=TokenAdmin, service=ServiceIdExpand)
    @autocommit
    def remove(self, service):
        """
        Archive service (only custom services can be deleted)

        :param Id service: Service Id
        :return: None
        """
        service.remove()
        return {}

    @staticmethod
    def paginate_services(services, limit, page):
        services = display(services)
        total = len(services)

        paginated_list = services[(page - 1) * limit:page * limit]

        res = {
            'per_page': limit,
            'total': total,
            'page': page,
            'items': paginated_list
        }
        return res

    # noinspection PyUnusedLocal
    @get('service/')
    @check_params(
        name=String,
        category=CategoryList,
        page=IntRange(1),
        limit=IntRange(1, conf.api.pagination.limit),
        sort=String,  # Sort(User.Meta.sort_fields),
        visibility=Visibility(),
        all_parameters=True
    )
    def list(self, name=None, category=None,
             page=1, limit=conf.api.pagination.limit,
             sort=None, visibility=Visibility.DEFAULT, all_parameters=True):
        """
        Return filtered list of services.

        :param str name: Filter for service name
        :param str category: Filter
        :param int page: page number
        :param int limit: number of items per page
        :param str visibility: Visibility options
                               *visible* - Only active services, [by default]
                               *deleted* - Only removed services.
                               *all* - All services.

        :return List service_list: List of services

        **Example**::

            {
                "service_list": {
                    "total": 20,
                    "per_page": 1,
                    "page": 1,
                    "items": [
                        {
                         "service_id":"net.associated_ip",
                         "localized_name":{ 
                            "ru":"net.associated_ip",
                            "en":"net.associated_ip"
                         },
                         "measure":{
                            "measure_id":"hour",
                            "localized_name":{
                               "ru":"\u0447\u0430\u0441",
                               "en":"hour"
                            },
                            "measure_type":"time"
                         },
                         "category":{
                            "localized_name":{
                               "ru":"\u0421\u0435\u0442\u044c",
                               "en":"Network"
                            },
                            "category_id":"net"
                        }
                    }
                ]
            }
        }

        """
        if category:
            category = frozenset(category)

        services = Service.list(only_categories=category, visibility=visibility)
        return {"service_list": self.paginate_services(services, limit, page)}

    # noinspection PyUnusedLocal
    @put('service/<service>/custom/')
    @check_params(
        token=TokenAccount,
        service=ServiceIdExpand,
        localized_name=LocalizedName,
        description=LocalizedName(requires_default_language=False),
        measure=MeasureTime
    )
    @autocommit
    def update_custom(self, service, localized_name=None, description=None, measure=None):
        """
        Update custom service. (only custom services can be updated)

        Parameters must be sent as json object.

        :param Id service: Service Id
        :param LocalizedName localized_name: Dict with name localization. en is mandatory key
                ``{"en": "Name", "ru": "\u0418\u043c\u044f"}``
        :param LocalizedName description: Dict with localized description.
        :param Measure measure: Measure id. Only time measure is possible.

        :return dict service_info: Dict as returned by
                                  :obj:`GET /0/service/\<service\>/ <view.GET /0/service/\<service\>>`
        """
        updated = service.update_custom(localized_name, description, measure)

        return {"service_info": display(service)}

    @put('service/<service>/vm/')
    @check_params(
        token=TokenAccount,
        service=ServiceIdExpand,
        localized_name=LocalizedName,
        description=LocalizedName(requires_default_language=False),
        measure=MeasureTime,
        flavor_id=String(),
        vcpus=Integer(),
        ram=Integer(),
        disk=Integer(),
        network=Integer(),
    )
    @autocommit
    def update_vm(self, token, service, localized_name=None, description=None,
                  flavor_id=None, vcpus=None, ram=None, disk=None, network=None):
        """
        Update Flavor.

        Parameters must be sent as json object.

        :param ServiceId service: Service Id
        :param LocalizedName localized_name: Dict with name localization. en is mandatory key
                ``{"en": "Name", "ru": "\u0418\u043c\u044f"}``
        :param LocalizedName description: Dict with localized description.
        :param flavor_id: Flavor name
        :param vcpus: Number of flavor's vcpus
        :param ram: flavor's RAM amount
        :param disk: flavor's disk size
        :param network: flavor's network

        :return dict service_info: Dict as returned by
                                  :obj:`GET /0/service/\<service\>/ <view.GET /0/service/\<service\>>`
        """
        flavor_info = dict(flavor_id=flavor_id, vcpus=vcpus, ram=ram, disk=disk, network=network)
        service.update_vm(localized_name, description, flavor_info)

        return {"service_info": display(service)}

    @put('service/<service>/immutable/')
    @check_params(
        token=TokenAccount,
        service=ServiceIdExpand,
    )
    @autocommit
    def immutable(self, service):
        """
        Make service immutable.

        :param Id service: Service Id.
        :return dict service_info: Dict as returned
        by :obj:`GET /0/service/\<service\>/ <view.GET /0/service/\<service\>>`
        """
        service.mark_immutable()

        return {"service_info": display(service)}
