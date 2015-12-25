import conf
import logbook
from celery import current_task
from datetime import timedelta
from celery import Celery
from celery.schedules import crontab
from celery.signals import after_setup_task_logger, worker_init, worker_shutdown
from celery.beat import PersistentScheduler
from utils import setup_backend_logbook, coverage_report
from functools import wraps
from memdb.mutex import RedisMutex
from memdb import MemDbModel
from raven import Client as RavenClient
from raven.contrib.celery import register_signal


include = ["task.mail", "task.customer", "task.openstack", "task.payments", "task.notifications", "task.main"]
redis_cfg = conf.memdb


EVERY_HOUR = crontab(minute=0)
EVERY_DAY = crontab(hour=0, minute=0)
EVERY_WEEK = crontab(day_of_week="sun", hour=0, minute=0)
EVERY_MONTH = crontab(day_of_month=1, hour=0, minute=0)
EVERY_QUARTER = crontab(month_of_year="1,4,7,10", day_of_month=1, hour=0, minute=0)


def get_cronmask(cronobj):
    assert isinstance(cronobj, crontab)
    return ("{0._orig_minute} {0._orig_hour} {0._orig_day_of_month} {0._orig_month_of_year} {0._orig_day_of_week}"
            .format(cronobj))


if not redis_cfg.sentinel:
    redis_url = 'redis://{}:{}'.format(*redis_cfg.hosts[0])
    celery = Celery('backend.celery',
                    broker=redis_url,
                    backend=redis_url,
                    include=include)
    celery.conf.update(CELERYD_MAX_TASKS_PER_CHILD=1,
                       CELERYD_CONCURRENCY=1,
                       CELERYD_POOL="solo")
else:
    from task.sentinel import register_celery_alias
    register_celery_alias()
    redis_url = 'redis-sentinel://'
    celery = Celery('backend.celery',
                    broker=redis_url,
                    backend=redis_url,
                    include=include)
    celery.conf.update(
        CELERY_REDIS_SENTINEL_SENTINELS=redis_cfg.hosts,
        CELERY_REDIS_SENTINEL_SERVICE_NAME=redis_cfg.sentinel,
        CELERY_REDIS_SENTINEL_SOCKET_TIMEOUT=redis_cfg.timeout,
        CELERY_REDIS_SENTINEL_SENTINEL_TIMEOUT=redis_cfg.sentinel_timeout,
        BROKER_TRANSPORT_OPTIONS={
            'service_name': redis_cfg.sentinel,
            'sentinels': redis_cfg.hosts,
            'sentinel_timeout': redis_cfg.sentinel_timeout,
            'socket_timeout': redis_cfg.timeout,
        }
    )

if conf.sentry.backend:
    client = RavenClient(dsn=conf.sentry.backend)
    register_signal(client)


def schedule_from_conf(conf):
    schedule = {}
    for k, v in conf.items():
        if isinstance(v['schedule'], int):
            v['schedule'] = timedelta(seconds=v['schedule'])
        elif isinstance(v['schedule'], dict):
            v['schedule'] = crontab(**v['schedule'])

        schedule.update({k: v})

    return schedule


celery.conf.update({
    'CELERYBEAT_SCHEDULER': 'task.main.SingletonScheduler',
    'CELERYBEAT_SCHEDULE': schedule_from_conf(conf.task.schedule),
    'CELERYBEAT_MAX_LOOP_INTERVAL': 60,
    'CELERY_ACCEPT_CONTENT': ['pickle', 'json', 'msgpack', 'yaml'],
    'CELERY_TASK_RESULT_EXPIRES': timedelta(hours=1),
    'CELERY_TIMEZONE': 'UTC',
})


if conf.test:
    celery.conf["CELERY_ALWAYS_EAGER"] = True


# noinspection PyUnusedLocal
@after_setup_task_logger.connect
def init_tasks_logger(**kwargs):
    handler = setup_backend_logbook("celery_worker")
    handler.push_application()


# Since Celery forks workers, wee need too call on_start() and on_exit() in each process
# noinspection PyUnusedLocal
@worker_init.connect
def on_worker_init(*args, **kwargs):
    if conf.devel.coverage_enable:
        config = conf.devel.coverage.copy()
        config['data_file'] += '.celery'
        coverage_report.coverage_on_start(config, False)


# noinspection PyUnusedLocal
@worker_shutdown.connect
def on_worker_shutdown(*args, **kwargs):
    if conf.devel.coverage_enable:
        coverage_report.coverage_on_exit()

if __name__ == '__main__':
    try:
        celery.start()
    except Exception as e:
        print("Exception in celery.start %s" % e)


def exception_safe_task(new_session=True, auto_commit=True, exp_countdown=True):
    from model import db
    from sqlalchemy.exc import OperationalError

    def outer(fn):
        def calc_exp_countdown():
            if conf.test:
                return 0

            if not exp_countdown:
                return None

            self_task = current_task
            return self_task.default_retry_delay ** (1.0 + float(self_task.request.retries) / 3.)

        @wraps(fn)
        def inner(*args, **kwargs):
            try:
                if new_session and not conf.test:
                    db.session.close()
                logbook.debug("Start task {} with args: {} {}", fn.__name__, args, kwargs)

                try:
                    h = "%8x" % abs(hash(args))
                except TypeError:
                    from pprint import pformat
                    h = hash(pformat(args))
                    h = "%8x" % abs(h)
                request_id = "%s-%s" % (fn.__name__, h[0:4])

                def inject_request_id(record):
                    record.extra['request_id'] = request_id

                with logbook.Processor(inject_request_id):
                    res = fn(*args, **kwargs)
                if auto_commit:
                    db.session.commit()
                logbook.debug("Result of task {}: {}", fn.__name__, res)
                return res
            except OperationalError as operation_error:
                logbook.warning("Database is down {}: {}", conf.database.uri, operation_error, exc_info=True)
                logbook.error("Database is down {}: {}", conf.database.uri, operation_error)
                db.session.close()
                current_task.retry(exc=operation_error, countdown=calc_exp_countdown())
            except Exception as exc:
                logbook.warning("{} failed. Retrying...", fn.__name__, exc_info=True)
                current_task.retry(exc=exc, countdown=calc_exp_countdown())
        return inner
    return outer


class SingletonScheduler(PersistentScheduler):
    def __init__(self, *args, **kwargs):
        super(SingletonScheduler, self).__init__(*args, **kwargs)
        self._mutex_ttl_ms = int(self.max_interval * 2 * 1000)
        self._mutex = RedisMutex(self.__class__.__name__, MemDbModel.redis)

    def tick(self):
        if not self._mutex.acquire(self._mutex_ttl_ms):
            return self.max_interval
        new_tick_interval = super(SingletonScheduler, self).tick()
        self._mutex_ttl_ms = ttl_ms = int((new_tick_interval+1) * 2 * 1000)
        self._mutex.update_ttl(ttl_ms)
        return new_tick_interval

    def close(self):
        super(SingletonScheduler, self).close()
        self._mutex.release()


def main():
    with setup_backend_logbook("celery_worker"):
        celery.start()


@celery.task()
def empty_task():
    logbook.info("Empty task is running")
    return True
