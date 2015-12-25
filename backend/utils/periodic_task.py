import logbook
import asyncio


class PeriodicTask:
    def __init__(self, interval, task_name=None):
        self.interval = interval
        self._stop = asyncio.Event()
        self.task_name = task_name or self.__class__.__name__

    def start(self):
        self._stop.clear()
        yield from self.run()

    def stop(self):
        self._stop.set()

    @asyncio.coroutine
    def run(self):
        logbook.info("Periodic task '{}' with period {} is run", self.task_name, self.interval)
        while not self._stop.is_set():
            self.task()
            yield from asyncio.sleep(self.interval)
        logbook.info("Periodic task '{}' is stopped", self.task_name, self.interval)

    def task(self):
        raise NotImplemented()
