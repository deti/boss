import logbook
from arrow import utcnow


def check_db_read():
    from model import User
    try:
        User.query.filter(User.user_id == 1).first()
    except Exception as e:
        logbook.warning(e)
        return str(e)


def check_db_write():
    from model import Option
    try:
        Option.set('last_check', utcnow().isoformat())
    except Exception as e:
        logbook.warning(e)
        return str(e)


def check_default_tariff():
    from model import Tariff
    return bool(Tariff.get_default().first())


def check_redis_write():
    from memdb import create_redis_client
    redis_health = {}
    redis = create_redis_client()
    try:
        redis_health['redis_write'] = redis.set('health_check', utcnow().isoformat())
    except Exception as e:
        logbook.warning(e)
        return str(e)


def check_redis_read():
    from memdb import create_redis_client
    redis = create_redis_client()
    try:
        redis.get('health_check')
    except Exception as e:
        logbook.warning(e)
        return str(e)


def check_openstack():
    from os_interfaces.openstack_wrapper import openstack
    try:
        openstack.check_openstack_availability()
    except Exception as e:
        logbook.warning(e)
        return str(e)


def check_ceilometer():
    from os_interfaces.openstack_wrapper import openstack
    try:
        openstack.client_ceilometer.new_samples.list(limit=10)
    except Exception as e:
        logbook.warning(e)
        return str(e)


def check_conf():
    import metayaml
    try:
        import conf
    except metayaml.MetaYamlException as e:
        return str(e)


def check_celery():
    from task.main import empty_task
    from celery.exceptions import TimeoutError

    result = empty_task.delay()
    try:
        result.get(30)
        return None
    except TimeoutError as e:
        return str(e)


def check_config(chk_celery=False):
    errors = {"conf": check_conf()}
    if errors["conf"]:
        return errors

    errors["db_read"] = check_db_read()
    errors["db_write"] = check_db_write()
    errors["default_tariff"] = None
    if errors["db_read"] is None and errors["db_write"] is None:
        if not check_default_tariff():
            errors["default_tariff"] = "Not configured"

    errors["redis_write"] = check_redis_write()
    errors["redis_read"] = check_redis_read()
    errors["openstack_api"] = check_openstack()
    errors["ceilometer"] = check_ceilometer()

    if chk_celery:
        errors["celery"] = check_celery()
    return errors


def print_check_config():
    from pprint import pformat
    from logbook import NullHandler

    with NullHandler():
        errors = check_config(chk_celery=True)
        if errors["conf"]:
            print("Configuration problem:", errors["conf"])
            return False

        import conf
        if errors["db_read"] or errors["db_write"]:
            print("Database configuration problem:", errors["db_read"] or errors["db_write"])
            print("Database uri:", conf.database.uri)

        if errors["default_tariff"]:
            print("Default tariff is not configured")

        if errors["redis_write"] or errors["redis_read"]:
            print("Redis configuration problem:", errors["redis_write"] or errors["redis_read"])
            print("Redis configuration:\n", pformat(conf.memdb))

        if errors["openstack_api"]:
            print("Openstack API is not available:", errors["openstack_api"])
            print("Openstack configuration:", pformat(conf.openstack))

        if errors["ceilometer"]:
            print("Ceilometer is not available:", errors["ceilometer"])
            print("Openstack configuration:", pformat(conf.openstack))

        if errors["ceilometer"]:
            print("Ceilometer is not available:", errors["ceilometer"])
            print("Openstack configuration:", pformat(conf.openstack))

        if errors["celery"]:
            print("Async tasks don't work:", errors["celery"])

    return not any(errors.values())
