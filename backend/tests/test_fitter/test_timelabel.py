import datetime
import unittest
from fitter.aggregation.timelabel import TimeLabel


class TestTimeLabel(unittest.TestCase):
    def test_utilization_time_label(self):
        self.assertEqual(TimeLabel(10 * 3600 + 30 * 60 + 1000 * 3600 * 24).label, "1972092710")
        self.assertEqual(TimeLabel(00 * 3600 + 00 * 60 + 1000 * 3600 * 24).label, "1972092700")

        start = 2 * 3600 + 1000 * 3600 * 24
        for x in range(start, start + 3600):
            self.assertEqual(TimeLabel(x).label, "1972092702")

        self.assertEqual(TimeLabel(datetime.datetime(2013, 2, 3, 4, 5, 6)).label, "2013020304")
        self.assertEqual(TimeLabel(datetime.date(2013, 2, 3)).label, "2013020300")

        t1 = TimeLabel.from_str("2013020311")
        t2 = TimeLabel.from_str("2013020312")
        t3 = TimeLabel.from_str("2013020315")
        self.assertEqual(t1 - t1, 0)
        self.assertEqual(t2 - t1, 1)
        self.assertEqual(t3 - t1, 4)
        self.assertEqual(t3 - t2, 3)

    def test_time_label_day(self):
        start = TimeLabel(datetime.datetime(2013, 2, 3, 4, 5, 6))
        finish = TimeLabel(datetime.datetime(2013, 2, 3, 4, 5, 7))
        self.assertEqual(list(TimeLabel.days(start, finish)), ["20130203"])

        finish = TimeLabel(datetime.datetime(2013, 2, 3, 4, 6, 7))
        self.assertEqual(list(TimeLabel.days(start, finish)), ["20130203"])

        finish = TimeLabel(datetime.datetime(2013, 2, 3, 4, 16, 7))
        self.assertEqual(list(TimeLabel.days(start, finish)), ["20130203"])

        finish = TimeLabel(datetime.datetime(2013, 2, 3, 5, 16, 7))
        self.assertEqual(list(TimeLabel.days(start, finish)), ["20130203"])

        finish = TimeLabel(datetime.datetime(2013, 2, 4, 5, 16, 7))
        self.assertEqual(list(TimeLabel.days(start, finish)), ["20130203", "20130204"])

        finish = TimeLabel(datetime.datetime(2013, 2, 5, 5, 16, 7))
        self.assertEqual(list(TimeLabel.days(start, finish)), ["20130203", "20130204", "20130205"])

        finish = TimeLabel(datetime.datetime(2013, 2, 5, 0, 0, 1))
        self.assertEqual(list(TimeLabel.days(start, finish)), ["20130203", "20130204", "20130205"])

        finish = TimeLabel(datetime.datetime(2013, 3, 5, 0, 0, 1))
        self.assertEqual(list(TimeLabel.days(start, finish)),
                         ["20130203", "20130204", "20130205", "20130206", "20130207",
                          "20130208", "20130209", "20130210", "20130211", "20130212",
                          "20130213", "20130214", "20130215", "20130216", "20130217",
                          "20130218", "20130219", "20130220", "20130221", "20130222",
                          "20130223", "20130224", "20130225", "20130226", "20130227",
                          "20130228", "20130301", "20130302", "20130303", "20130304", "20130305"])
