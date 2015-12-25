from collections import namedtuple
import time
import pytest


def read(path=None, set_globals=True):
    import os
    import metayaml
    from attrdict import AttrDict
    from lib import root_directory, config_stage_directory

    def fix_me():
        print("fixme")
        raise Exception("Please fill parameter")

    stage_config = os.environ.get('BOSS_CONFIG', None)
    custom_stage_config = pytest.config.getoption('stage_config')
    test_config = os.path.join(root_directory(), 'tests', 'configs', 'default.yaml')
    custom_test_config = pytest.config.getoption('test_config')

    configs = list()

    configs.append(test_config)

    if path:
        configs.append(path)
    elif custom_stage_config:
        configs.append(custom_stage_config)
    elif stage_config:
        configs.append(stage_config)
    else:
        raise ValueError("No stage config specified. Ether set env BOSS_CONFIG or specify argument --stage_config for tests")

    if custom_test_config:
        configs.append(custom_test_config)

    config = metayaml.read(configs,
                           defaults={
                               "__FIX_ME__": fix_me,
                               "STAGE_DIRECTORY": config_stage_directory(),
                               "join": os.path.join,
                               "ROOT": root_directory()
                           })

    if not config['backend']['entry_point']:
        config['backend']['entry_point'] = 'http://localhost:8080'

    config = AttrDict(config, recursive=True)
    if set_globals:
        for k in config.keys():
            if k == "__FIX_ME__":
                continue
            v = getattr(config, k)
            globals()[k] = v

    return config

read()

load_time = time.time()

del globals()['time']

if 'promocodes' not in globals():
    globals()['promocodes'] = namedtuple('promocodes', ['promo_registration_only', 'codes'])(
        promo_registration_only=False, codes=dict())