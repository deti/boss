import argparse
from collections import OrderedDict
import json
import metayaml
import os
import yaml
from contextlib import contextmanager
from teamcity import messages


def skip_test(func):
    func.__skip__ = True
    return func


class TestError(Exception): pass


class TeamcityMessages(messages.TeamcityServiceMessages):
    devnull = open(os.devnull, 'w')

    def __init__(self, enabled:bool=False):
        if enabled:
            super().__init__()
        else:
            super().__init__(self.devnull)

    def buildStatus(self, text, status=None):
        self.message('buildStatus', text=text, status=status)

    @contextmanager
    def test_suite_context(self, test_name):
        self.testSuiteStarted(test_name)
        try:
            yield
        except Exception as e:
            self.buildStatus('%s failed' % test_name)
            raise
        finally:
            self.testSuiteFinished(test_name)

    @contextmanager
    def test_context(self, test_name):
        self.testStarted(test_name)
        try:
            yield
        except Exception as e:
            self.testFailed(test_name, e.__class__.__name__+':'+str(e), '')
            raise
        else:
            self.testFinished(test_name)


def _convert_ordered_dict(d: dict):
    for key in d:
        if isinstance(d[key], OrderedDict):
            d[key] = dict(d[key])
        if isinstance(d[key], dict):
            d[key] = _convert_ordered_dict(d[key])
    return d


def _get_doc_from_shema(shema: dict) -> str:
    return "Config file format:\n" + '-'*10 + '\n' + yaml.dump(shema, default_flow_style=False) + '-'*10


def _validate_shema(shema:dict, config:dict, raise_error:bool=True, parser=None):
    for key, value in shema.items():
        if key not in config:
            message = 'Key "%s" not found in config keys: %s' % (key, list(config.keys()))
            if raise_error:
                raise argparse.ArgumentTypeError(message)
            else:
                parser.error(message)
        if isinstance(value, dict):
            _validate_shema(value, config[key])


def _get_arguments() -> dict:
    shema = metayaml.read(os.path.join(os.path.dirname(__file__), 'config_template.yaml'))
    shema = _convert_ordered_dict(shema)

    parser = argparse.ArgumentParser('BOSS Light Tests', formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description=_get_doc_from_shema(shema))

    parser.add_argument('-o', '--openstack', help='Enable openstack test', action='store_true')
    parser.add_argument('-v', '--verbose', help='Be verbose', action='store_true')
    parser.add_argument('-t', '--teamcity', help='Enable teamcity messages', action='store_true')
    parser.add_argument('--test_label', type=str, help='Tests label', default=None, required=False)

    def config_validate(path:str) -> dict:
        if path.endswith('.yaml'):
            config_reader = lambda path: metayaml.read(path)
        elif path.endswith('.json'):
            config_reader = lambda path: json.load(open(path, 'r'))
        else:
            raise argparse.ArgumentTypeError('unsupported config file format: {}'.format(path.split('.')[-1]))
        try:
            config = config_reader(path)
        except OSError as e:
            raise argparse.ArgumentTypeError("can't open '%s': %s" % (path, e))

        base_shema = shema.copy()
        base_shema.pop('openstack', None)
        _validate_shema(base_shema, config)

        return config

    parser.add_argument('config', type=config_validate, metavar='config_file', help='Config file (yaml, json)')

    args = parser.parse_args()

    if args.openstack:
        _validate_shema(shema, args.config, False, parser)
        try:
            import light_tests.clients.openstack
        except ImportError as e:
            raise ValueError('Openstack tests are enabled but import error occured: {}'.format(e))

    args.config = _convert_ordered_dict(args.config)

    return vars(args)
