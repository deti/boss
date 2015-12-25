import conf
import logbook
import msgpack
from memdb import MemDbModel
from collections import namedtuple


Quota = namedtuple('Quota', ['used', 'ttl', 'fresh', 'live_time'])


class QuotaCache(MemDbModel):
    """ Used for storing customer used quotas.
    """
    _prefix = "quota:"

    def key(self, customer):
        return self._prefix + str(customer.customer_id)

    def set(self, customer, quotas):
        self.redis.setex(self.key(customer), conf.customer.quota.ttl, self.pack(quotas))

    def get(self, customer):
        key = self.key(customer)
        res = self.redis.get(key)
        if res is None:
            return None

        try:
            used = self.unpack(res)
        except Exception as e:
            logbook.error("Corrupted quotas for customer {}: {}", customer, e)
            return None

        ttl = self.redis.ttl(key)

        live_time = conf.customer.quota.ttl - ttl
        fresh = live_time < conf.customer.quota.fresh
        return Quota(used, ttl, fresh, live_time)

    @staticmethod
    def pack(quotas):
        return msgpack.packb(quotas, use_bin_type=True)

    @staticmethod
    def unpack(packed):
        return msgpack.unpackb(packed, encoding='utf-8')
