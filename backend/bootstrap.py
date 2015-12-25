"""Bootstrap backend entities.

Usage:
    bootstrap.py <stage_config> <entity_config> [-u] [-v]
    bootstrap.py <entity_config> -e EMAIL -p PASSWORD [--url=URL] [-u] [-v]

Options:
    -h --help               Show this screen.
    stage_config FILE       Stage config. Can be stage name, stage config filename, or stage config path.
    entity_config FILE      Entity config.
    -e --email EMAIL        Backend admin email.
    -p --password PASSWORD  Backend admin password.
    --url URL               Backend entry point url. [default: http://localhost:8080]
    -u --update             Update entity if exists (default - only compare) [default: False]
    -v --verbose            Enable verbose mode. [default: False]

Tariff entity format help:
    To create tariff with services, you can:
    localized_name: ...
    currency: ...
    description: ...
    services:
        service_id: price
        service_id2: price
        ...
    where service_id can be either real service id (1124) or flavor_id (Nano, Micro)
"""
from decimal import Decimal
import logbook
from utils import find_first
from utils.bootstrap import BootstraperBase
from boss_client.adminbackend import AdminBackendClient


class BackendBootstrap(BootstraperBase):
    need_update = False

    def __init__(self, entry_point, admin_email, admin_password, update: bool=False, verbose: bool=False):
        logbook.default_handler.level = logbook.DEBUG if verbose else logbook.INFO
        self.client = AdminBackendClient(entry_point)
        self.client.login(admin_email, admin_password)
        self.update = update
        self.verbose = verbose

    def process_doc(self, filename):
        super().process_doc(filename)
        if self.need_update and not self.update:
            logbook.info('Some fields are different. Add an -u (--update) key to update these fields.\n"'
                         'First is entity value, second is config value')

    def compare_fields(self, entity_dict: dict, config_dict: dict, fields: list=None) -> list:
        """ Do some automatic fields comparing. If 'fields' is None, compare all fields. Return true
        if at least one field not equal """
        diff = []
        for key, config_value in config_dict.items():
            if (fields is None or key in fields) and (key in entity_dict):
                entity_value = entity_dict[key]
                if entity_value != config_value:
                    diff.append((key, entity_value, config_value))
        return diff

    def diff_to_str(self, entity_name, diff: list) -> str:
        self.need_update = True
        msg = entity_name + ' diff:\n\t'
        msg += '\n\t'.join('{}: "{}" != "{}"'.format(*values) for values in diff)
        return msg

    def create_tariff(self, params=None):
        messages = []
        can_modify = self.update

        immutable = params.pop('immutable', False)
        default = params.pop('default', False)
        parsed_services = []
        for service_id, price in params.pop('services', {}).items():
            flavor = self.get_flavor(service_id)
            if flavor:
                service_id = flavor['service_id']
            parsed_services.append({'service_id': service_id, 'price': price})
        params['services'] = parsed_services

        tariff_list = self.client.tariff.list(name=params['localized_name']['en'])
        if tariff_list['total'] == 0:
            tariff_info = self.client.tariff.create(**params)
            logbook.info('Tariff "{}" created with id={}'.format(tariff_info['localized_name']['en'],
                                                                 tariff_info['tariff_id']))
            can_modify = True
        else:
            tariff_info = tariff_list['items'][0]
            diff = self.compare_fields(tariff_info, params, ['localized_name', 'description', 'currency'])
            for service_config in params['services']:
                service_id, price = service_config['service_id'], str(service_config['price'])
                service = find_first(tariff_info['services'], lambda srv: service_id == srv['service']['service_id'])
                if not service:
                    messages.append('Service "{}" (id:{}) not in tariff service list'.format(
                        service['service']['localized_name']['en'], service_id))
                elif Decimal(price) != Decimal(service['price']):
                    diff.append(('service price ({})'.format(service['service']['localized_name']['en']),
                                 service['price'], price))

            if diff or messages:
                diff_str = self.diff_to_str('Tariff "{}" (id:{})'.format(tariff_info['localized_name']['en'],
                                                                         tariff_info['tariff_id']), diff)
                logbook.info(diff_str)
                for message in messages:
                    logbook.info(message)
                if not tariff_info['mutable']:
                    logbook.warning('Tariff is immutable')
                if tariff_info['mutable'] and self.update:
                    self.client.tariff.update(tariff_info['tariff_id'], **params)

        if immutable and can_modify:
            self.client.tariff.immutable(tariff_info['tariff_id'])
        if default and can_modify:
            self.client.tariff.set_default(tariff_info['tariff_id'])

    def create_customer(self, params=None):
        confirmed = params.pop('confirmed', False)
        can_modify = self.update

        customer_list = self.client.customer.list(email=params['email'])
        if customer_list['total'] == 0:
            customer_info = self.client.customer.create(**params)
            logbook.info('Customer "{}" created with id={}'.format(customer_info['email'],
                                                                   customer_info['customer_id']))
            can_modify = True
        else:
            customer_info = customer_list['items'][0]
            params.pop('email')
            diff = self.compare_fields(customer_info, params, ['locale'])
            diff.extend(self.compare_fields(customer_info['detailed_info'], params['detailed_info']))
            if diff:
                diff_str = self.diff_to_str('Customer "{}" (id:{})'.format(customer_info['email'],
                                                                           customer_info['customer_id']), diff)
                logbook.info(diff_str)
                if self.update:
                    self.client.customer.update(customer_info['customer_id'], **params)

        if confirmed and can_modify:
            self.client.customer.update(customer_info['customer_id'], confirm_email=True)

    def create_user(self, params=None):
        user_list = self.client.user.list(email=params['email'])
        if user_list['total'] == 0:
            user_info = self.client.user.create(**params)
            logbook.info('User "{}" created with id={}'.format(user_info['email'], user_info['customer']))
        else:
            user_info = user_list['items'][0]
            diff = self.compare_fields(user_info, params, ['email', 'name'])
            if user_info['role']['role_id'] != params['role']:
                diff.append(('role', user_info['role']['role_id'], params['role']))
            if diff:
                diff_str = self.diff_to_str('User "{}" (id:{})'.format(user_info['email'], user_info['user_id']), diff)
                logbook.info(diff_str)
                if self.update:
                    self.client.user.update(user_info['user_id'], **params)

    def create_news(self, params=None):
        published = params.pop('published', False)
        news_info = self.client.news.create(**params)
        logbook.info('News "{}" created with id={}'.format(news_info['subject'], news_info['news_id']))
        if published:
            self.client.news.publish(news_info['news_id'], True)

    def create_service(self, params=None):
        can_modify = self.update

        immutable = params.pop('immutable', False)

        service_list = self.client.service.list()
        service_list = filter(lambda service: service['localized_name'] == params['localized_name'],
                              service_list['items'])
        service_info = next(service_list, None)
        if not service_info:
            service_info = self.client.service.create(**params)
            logbook.info('Service "{}" created with id={}'.format(service_info['localized_name']['en'],
                                                                  service_info['service_id']))
            can_modify = True
        else:
            diff = self.compare_fields(service_info, params, ['localized_name', 'description'])
            if service_info['measure']['measure_id'] != params['measure']:
                diff.append(('measure', service_info['measure']['measure_id'], params['measure']))
            if diff:
                diff_str = self.diff_to_str('Service <{}>'.format(service_info['service_id']), diff)
                logbook.info(diff_str)
                if not service_info['mutable']:
                    logbook.warning('Service is immutable')
                if service_info['mutable'] and self.update:
                    self.client.service.update(service_info['service_id'], **params)

        if immutable and can_modify:
            self.client.service.immutable(service_info['service_id'])

    def create_flavor(self, params=None):
        can_modify = False
        immutable = params.pop('immutable', False)

        flavor_id = params["flavor_id"]
        flavor = self.get_flavor(flavor_id)
        if not flavor:
            service_info = self.client.service.create_vm(**params)
            logbook.info('Flavor "{}" created with id={}'.format(service_info['localized_name']['en'],
                                                                 service_info['service_id']))
            can_modify = True
        else:
            service_info = flavor
            params.pop('flavor_id')
            diff = self.compare_fields(service_info, params, ['localized_name'])
            diff.extend(self.compare_fields(service_info['flavor'], params, list(service_info['flavor'].keys())))
            if diff:
                diff_str = self.diff_to_str('Flavor "{}" (id:{})'.format(service_info['localized_name']['en'],
                                                                         service_info['service_id']), diff)
                logbook.info(diff_str)
                if not service_info['mutable']:
                    logbook.warning('Service is immutable')
                if service_info['mutable'] and self.update:
                    self.client.service.update_vm(service_info['service_id'], **params)

        if immutable and can_modify:
            self.client.service.immutable(service_info['service_id'])

    def get_flavor(self, flavor_id):
        flavor_list = self.list_flavors()
        for flavor in flavor_list["items"]:
            if flavor["flavor"]["flavor_id"] == flavor_id:
                return flavor
        return None

    def list_flavors(self):
        return self.client.service.list(category="vm")


def main():
    import docopt
    import metayaml
    import os
    import lib
    args = docopt.docopt(__doc__)

    stage_config = args['<stage_config>']
    if stage_config:
        config_path = stage_config
        if not os.path.exists(config_path):
            config_path = os.path.join(lib.config_stage_directory(), config_path)
            if not os.path.exists(config_path):
                config_path += '.yaml'
                if not os.path.exists(config_path):
                    print('Stage config "{}" not found.'.format(stage_config))
                    return
        configs = [os.path.join(lib.root_directory(), "backend", "configs", "backend.yaml"), config_path]

        def fix_me():
            print("fixme")

        def replace_db(uri, database):
            from sqlalchemy.engine.url import make_url
            u = make_url(uri)
            u.database = database
            return u.__to_string__(hide_password=False)

        config = metayaml.read(configs, defaults={
                               "__FIX_ME__": fix_me,
                               "STAGE_DIRECTORY": lib.config_stage_directory(),
                               "join": os.path.join,
                               "ROOT": lib.root_directory(),
                               "environ": os.environ,
                               "replace_db": replace_db})
        bootstrap = BackendBootstrap(config['backend']['entry_point'], config['user']['default_users'][0]['email'],
                                     config['user']['default_users'][0]['password'],
                                     args['--update'], args['--verbose'])
    else:
        bootstrap = BackendBootstrap(args['--url'], args['--email'], args['--password'],
                                     args['--update'], args['--verbose'])

    bootstrap.process_doc(args['<entity_config>'])


if __name__ == '__main__':
    exit(main())
