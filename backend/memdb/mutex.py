import binascii
import logbook
import time
from os import urandom


class RedisMutex:
    """ Distributed mutex with ttl.
    """
    prefix = "mutex:"

    def __init__(self, name, redis, token_length=4, ttl_ms=None):
        self.name = name
        self.redis = redis
        self._token = urandom(token_length)
        self.ttl_ms = ttl_ms
        self.acquired = None
        # snippet from http://redis.io/commands/set
        self._delete_lock_cmd = self.redis.register_script("""
        if redis.call("get", KEYS[1]) == ARGV[1]
        then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """)

    @property
    def key(self):
        return self.prefix + self.name

    def __str__(self):
        return "<RedisMutex '%s' (%s) acquired: %s>" % (self.name, binascii.hexlify(self._token).decode("ascii"),
                                                        self.acquired)

    def acquire(self, ttl_ms=None):
        # NOTE: blocking until mutex available is not implemented
        ttl_ms = ttl_ms or self.ttl_ms
        assert ttl_ms
        token = self.redis.get(self.key)
        if token is None:
            if not self.redis.set(self.key, self._token, px=ttl_ms, nx=True):
                logbook.debug("RedisMutex '{}' was acquired during acquiring", self.name)
                return False
        elif token != self._token:
            logbook.debug("RedisMutex '{}' is already acquired by token {}", self.name,
                          binascii.hexlify(token).decode("ascii"))
            return False

        logbook.info("{} is acquired for {} ms", self, ttl_ms)
        self.acquired = time.time()

        return True

    def release(self):
        if not self.acquired:
            logbook.debug("Release skipping for {}", self)
            return False

        res = self._delete_lock_cmd([self.key], [self._token])
        acquiring_time = time.time() - self.acquired
        self.acquired = None
        if res:
            logbook.info("{} is released. Acquiring was {:.3f} seconds", self, acquiring_time)
            return True
        logbook.error("{} release failed {}. Acquired was {:.3f} seconds ago", self, res, acquiring_time)
        return False

    def update_ttl(self, ttl_ms=None):
        # NOTE it's not really safe in concurrent environment
        logbook.debug("{} update_ttl", self)
        return self.redis.set(self.key, self._token, px=ttl_ms or self.ttl_ms)

    def __enter__(self):
        return self if self.acquire() else False

    # noinspection PyUnusedLocal
    def __exit__(self, t, v, tb):
        self.release()
