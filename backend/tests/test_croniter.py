from utils.croniter import croniter
from unittest import TestCase
from datetime import datetime

class TestCronIter(TestCase):
    def test_croniter(self):
        current_time = datetime(2015, 7, 31, 13, 17, 28, 33)
        cron = croniter("* * * * * *", current_time)
        self.assertEqual(cron.get_next(datetime), datetime(2015, 7, 31, 13, 17, 29))
        self.assertEqual(cron.get_next(datetime), datetime(2015, 7, 31, 13, 17, 30))

        with self.assertRaises(ValueError):
            cron = croniter("asdfas df", current_time)
