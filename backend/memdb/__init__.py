import conf

from redis import sentinel, StrictRedis


def create_redis_client(db=None):
    c = conf.memdb
    if db is None:
        db = c.db_main_index
    if conf.test:
        db += c.db_index_test_offset
    if c.sentinel:
        sent = sentinel.Sentinel(c.hosts, socket_timeout=c.sentinel_timeout, socket_keepalive=True)
        return sent.master_for(c.sentinel, socket_timeout=c.timeout, db=db)
    else:
        host, port = c.hosts[0]
        return StrictRedis(host=host, port=port, db=db, socket_keepalive=True)


class MemDbModel(object):

    redis = create_redis_client()
    _key_prefix = ""
    _key_join_symbol = "-"

    @classmethod
    def clear(cls):
        cls.redis.flushdb()

    @classmethod
    def prefixed(cls, *parts):
        return cls._key_join_symbol.join(parts)

    @classmethod
    def prefixed_key(cls, *parts):
        return cls._key_prefix + cls._key_join_symbol.join(parts)


def clear_mem_db():
    if not conf.test:
        raise Exception("clear_redis is called for not test configuration")

    MemDbModel().clear()
