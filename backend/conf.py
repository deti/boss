def read():
    import os
    import metayaml
    from attrdict import AttrDict
    from lib import root_directory, config_stage_directory
    from os import environ

    GLOBAL_STAGE_CONFIG = "/etc/boss.yaml"

    class PleaseFillRequiredParameter(Exception):
        pass

    def replace_db(uri, database):
        from sqlalchemy.engine.url import make_url
        u = make_url(uri)
        u.database = database
        return u.__to_string__(hide_password=False)

    def fix_me():
        raise PleaseFillRequiredParameter("Please fill parameter")

    stage_config = GLOBAL_STAGE_CONFIG if os.path.isfile(GLOBAL_STAGE_CONFIG) else \
        os.environ.get("BOSS_CONFIG", os.path.join(config_stage_directory(), "dev_local.yaml"))

    configs = [os.path.join(root_directory(), "backend", "configs", "backend.yaml"), stage_config]
    config = metayaml.read(configs,
                           defaults={
                               "__FIX_ME__": fix_me,
                               "STAGE_DIRECTORY": config_stage_directory(),
                               "join": os.path.join,
                               "ROOT": root_directory(),
                               "environ": environ,
                               "replace_db": replace_db
                           })

    config = AttrDict(config, recursive=True)
    for k in config.keys():
        if k == "__FIX_ME__":
            continue
        v = getattr(config, k)
        globals()[k] = v

    return config

read()

del globals()['read']
