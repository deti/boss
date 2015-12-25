# -*- coding: utf-8 -*-
import time
from tests.base import BaseTestCaseDB

from memdb import MemDbModel
from memdb.mutex import RedisMutex


class RedisMutexTest(BaseTestCaseDB):
    def test_lock(self):
        l = RedisMutex("test", MemDbModel.redis, ttl_ms=10000)
        self.assertTrue(l.acquire())
        m = RedisMutex("test", MemDbModel.redis, ttl_ms=10000)
        self.assertFalse(m.acquire())
        self.assertTrue(l.release())
        self.assertFalse(l.release())
        self.assertFalse(m.release())

    def test_reacquiring(self):
        l = RedisMutex("test_reacquiring", MemDbModel.redis, ttl_ms=10000)
        self.assertTrue(l.acquire())
        l.redis.set(l.key, "test")
        self.assertFalse(l.release())

    def test_expiring(self):
        l = RedisMutex("test_test_expiring", MemDbModel.redis, ttl_ms=400)
        self.assertTrue(l.acquire())
        time.sleep(1)
        self.assertTrue(l.acquire())
        self.assertTrue(l.release())

    def test_context(self):
        with RedisMutex("test_test_expiring", MemDbModel.redis, ttl_ms=10000) as l:
            self.assertTrue(l)
            new_lock = RedisMutex("test_test_expiring", MemDbModel.redis, ttl_ms=10000)
            self.assertFalse(new_lock.acquire())

        new_lock = RedisMutex("test_test_expiring", MemDbModel.redis, ttl_ms=10000)
        self.assertTrue(new_lock.acquire())

        with RedisMutex("test_test_expiring", MemDbModel.redis, ttl_ms=10000) as l:
            self.assertFalse(l)
