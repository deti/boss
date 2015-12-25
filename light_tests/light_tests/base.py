from contextlib import contextmanager
import time
from light_tests.tools import TeamcityMessages


class LightTestsBase:
    _tests_list = list()

    def __init__(self, config:dict, test_label:str=None, openstack:bool=False, verbose:bool=False, teamcity:bool=False):
        self.config = config
        self.openstack = openstack
        self.verbose = verbose
        self.test_label = test_label or 'LightTests'
        self.teamcity = teamcity
        self.current_test_name = None

    @classmethod
    def add_test(cls, func):
        cls._tests_list.append(func)
        return func

    def print(self, message):
        if self.verbose:
            print('[%s:%s]' % (self.test_label, self.current_test_name), message)

    def get_tests(self) -> list:
        for func in self._tests_list:
            func_name = func.__name__
            skip = getattr(func, '__skip__', False)
            yield func_name, func, skip

    def run(self):
        teamcity_messages = TeamcityMessages(self.teamcity)
        with teamcity_messages.test_suite_context(self.test_label):
            for test_name, test_func, skip in self.get_tests():
                self.current_test_name = test_name
                if skip:
                    teamcity_messages.testIgnored(test_name, 'Test skipped')
                    self.print('Test skipped')
                    continue
                with teamcity_messages.test_context(test_name):
                    self.print('Started')
                    try:
                        test_func(self)
                    except Exception as e:
                        if not self.handle_error(e):
                            raise
                    self.print('Finished')

    def handle_error(self, error) -> bool:
        return False

    def retries(self, timeout=5, sleep_time=0.5, exception=AssertionError, sleep=time.sleep):
        timeout_at = time.time() + timeout
        state = {"fails_count": 0, "give_up": False, "success": False}
        while time.time() < timeout_at:
            yield self._handler(exception, state)
            if state["success"]:
                return
            sleep(sleep_time)
        state["give_up"] = True
        yield self._handler(exception, state)

    @contextmanager
    def _handler(self, exception, state):
        try:
            yield
        except exception:
            state["fails_count"] += 1
            if state["give_up"]:
                raise
        else:
            state["success"] = True