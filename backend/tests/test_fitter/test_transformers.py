# -*- coding: utf-8 -*-
import mock
import unittest
import datetime

from tests.base import BaseTestCaseDB
from fitter.aggregation.timelabel import TimeLabel
import fitter.aggregation.transformers as transformers
from fitter.aggregation import constants
from fitter.aggregation.constants import states
from operator import attrgetter
from ceilometerclient.v2.samples import OldSample
from model import Service
from os_interfaces.openstack_wrapper import openstack


def p(timestr):
    return datetime.datetime.strptime(timestr, constants.date_format)


class testdata:
    # string timestamps to put in meter data
    t0 = p('2015-01-01T00:00:00')
    t0_10 = p('2015-01-01T00:10:00')
    t0_20 = p('2015-01-01T00:30:00')
    t0_30 = p('2015-01-01T00:30:00')
    t0_40 = p('2015-01-01T00:40:00')
    t0_50 = p('2015-01-01T00:50:00')
    t1 = p('2015-01-01T01:00:00')

    # and one outside the window
    tpre = p('2014-12-31T23:50:00')

    flavor = 'Nano'
    flavor2 = 'Micro'
    fake_flavor = 'FakeFlavor'


class TestMeter(object):
    def __init__(self, data, mtype=None):
        self.data = data
        self.type = mtype

    def usage(self):
        return self.data


class BaseTransformTest(unittest.TestCase):
    @staticmethod
    def make_sample(data):
        return [OldSample(None, event) for event in data]

    def test_max_volume(self):
        """
        Test empty volume value
        """
        data = [
            {'timestamp': testdata.t0, 'counter_volume': None},
            {'timestamp': testdata.t0_10, 'counter_volume': None},
            {'timestamp': testdata.t0_20, 'counter_volume': None},
            {'timestamp': testdata.t0_30, 'counter_volume': None},
            {'timestamp': testdata.t0_40, 'counter_volume': None},
            {'timestamp': testdata.t0_50, 'counter_volume': None},
            {'timestamp': testdata.t1, 'counter_volume': None},
        ]
        xform = transformers.GaugeMax()
        usage = xform.transform_usage('some_meter', self.make_sample(data), TimeLabel(testdata.t0))

        self.assertEqual(usage[0].volume, 0)

        data = [
            {'timestamp': testdata.t0, 'volume': None},
            {'timestamp': testdata.t0_10, 'volume': None},
            {'timestamp': testdata.t0_20, 'volume': None},
            {'timestamp': testdata.t0_30, 'volume': None},
            {'timestamp': testdata.t0_40, 'volume': None},
            {'timestamp': testdata.t0_50, 'volume': None},
            {'timestamp': testdata.t1, 'volume': None},
        ]
        xform = transformers.GaugeMax()
        usage = xform.transform_usage('some_meter', self.make_sample(data), TimeLabel(testdata.t0))

        self.assertEqual(usage[0].volume, 0)



class UptimeTransformerTests(BaseTestCaseDB, BaseTransformTest):

    def _run_transform(self, data):
        xform = transformers.Uptime()
        return xform.transform_usage('state', self.make_sample(data), TimeLabel(testdata.t0))

    def test_trivial_run(self):
        """
        Test that an no input data produces empty uptime.
        """
        state = []
        result = self._run_transform(state)
        self.assertEqual([], result)

    def test_online_constant_flavor(self):
        """
        Test that a machine online for a 1h period with constant
        flavor works and gives 1h of uptime.
        """
        state = [
            {'timestamp': testdata.t0, 'counter_volume': states['active'],
                'metadata': {'flavor.name': testdata.flavor}},
            {'timestamp': testdata.t1, 'counter_volume': states['active'],
                'metadata': {'flavor.name': testdata.flavor}}
        ]

        result = self._run_transform(state)
        # there should be one hour of usage.
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].end - result[0].start, datetime.timedelta(hours=1, seconds=-1))

    def test_offline_constant_flavor(self):
        """
        Test that a machine offline for a 1h period with constant flavor
        works and gives zero uptime.
        """

        state = [
            {'timestamp': testdata.t0, 'counter_volume': states['stopped'],
                'metadata': {'flavor.name': testdata.flavor}},
            {'timestamp': testdata.t1, 'counter_volume': states['stopped'],
                'metadata': {'flavor.name': testdata.flavor}}
        ]

        result = self._run_transform(state)
        # there should be no usage, the machine was off.
        self.assertEqual([], result)

    def test_shutdown_during_period(self):
        """
        Test that a machine run for 0.5 then shutdown gives 0.5h uptime.
        """
        state = [
            {'timestamp': testdata.t0, 'counter_volume': states['active'],
                'metadata': {'flavor.name': testdata.flavor}},
            {'timestamp': testdata.t0_30, 'counter_volume': states['stopped'],
                'metadata': {'flavor.name': testdata.flavor}},
            {'timestamp': testdata.t1, 'counter_volume': states['stopped'],
                'metadata': {'flavor.name': testdata.flavor}}
        ]

        result = self._run_transform(state)
        # there should be half an hour of usage.
        self.assertEqual(result[0].end - result[0].start, datetime.timedelta(seconds=1800))

    def test_online_flavor_change(self):
        """
        Test that a machine run for 0.5h as m1.tiny, resized to m1.large,
        and run for a further 0.5 yields 0.5h of uptime in each class.
        """
        state = [
            {'timestamp': testdata.t0, 'counter_volume': states['active'],
                'metadata': {'flavor.name': testdata.flavor}},
            {'timestamp': testdata.t0_30, 'counter_volume': states['active'],
                'metadata': {'flavor.name': testdata.flavor2}},
            {'timestamp': testdata.t1, 'counter_volume': states['active'],
                'metadata': {'flavor.name': testdata.flavor2}}
        ]

        result = self._run_transform(state)
        self.assertEqual(len(result), 2)
        # there should be half an hour of usage in each of m1.tiny and m1.large

        result.sort(key=attrgetter("service_id"))
        self.assertEqual(result[0].service_id, self.service_nano_id)
        self.assertEqual(result[0].end - result[0].start, datetime.timedelta(minutes=30))
        self.assertEqual(result[1].service_id, self.service_micro_id)
        self.assertEqual(result[1].end - result[1].start, datetime.timedelta(minutes=30, seconds=-1))

    def test_period_leadin_none_available(self):
        """
        Test that if the first data point is well into the window, and we had
        no lead-in data, we assume no usage until our first real data point.
        """
        state = [
            {'timestamp': testdata.t0_10, 'counter_volume': states['active'],
                'metadata': {'flavor.name': testdata.flavor}},
            {'timestamp': testdata.t1, 'counter_volume': states['active'],
                'metadata': {'flavor.name': testdata.flavor}}
        ]

        result = self._run_transform(state)
        # there should be 50 minutes of usage; we have no idea what happened
        # before that so we don't try to bill it.
        self.assertEqual(result[0].end - result[0].start, datetime.timedelta(minutes=50, seconds=-1))

    def test_period_leadin_available(self):
        """
        Test that if the first data point is well into the window, but we *do*
        have lead-in data, then we use the lead-in clipped to the start of the
        window.
        """
        state = [
            {'timestamp': testdata.tpre, 'counter_volume': states['active'],
                'metadata': {'flavor.name': testdata.flavor}},
            {'timestamp': testdata.t0_10, 'counter_volume': states['active'],
                'metadata': {'flavor.name': testdata.flavor}},
            {'timestamp': testdata.t1, 'counter_volume': states['active'],
                'metadata': {'flavor.name': testdata.flavor}}
        ]

        result = self._run_transform(state)
        # there should be 60 minutes of usage; we have no idea what
        # happened before that so we don't try to bill it.
        self.assertEqual(result[0].end - result[0].start, datetime.timedelta(hours=1, seconds=-1))

    def test_for_nonexistent_flavor(self):
        """
        Tests that transformer doesn't stop when flavor.name isn't in database and creates fake entry in DB for that
        flavor.
        """
        state = [
            {'timestamp': testdata.t0, 'counter_volume': states['active'],
                'metadata': {'flavor.name': testdata.flavor}},
            {'timestamp': testdata.t0_30, 'counter_volume': states['active'],
                'metadata': {'flavor.name': testdata.fake_flavor}},
            {'timestamp': testdata.t1, 'counter_volume': states['active'],
                'metadata': {'flavor.name': testdata.fake_flavor}}
        ]

        with mock.patch('os_interfaces.openstack_wrapper.openstack.get_nova_flavor',
                        mock.MagicMock(side_effect=self.create_flavor_mock)):
            result = self._run_transform(state)

            result.sort(key=attrgetter("service_id"))

            flavor = Service.get_by_id(result[1].service_id).flavor

            self.assertEqual(flavor.flavor_id, testdata.fake_flavor)
            self.assertEqual(openstack.get_nova_flavor.call_count, 1)
            self.assertEqual(openstack.create_flavor.call_count, 10)
            self.assertEqual(result[1].end - result[1].start, datetime.timedelta(minutes=30, seconds=-1))


class GaugeMaxTransformerTests(BaseTransformTest):

    def test_all_different_values(self):
        """
        Tests that the transformer correctly grabs the highest value,
        when all values are different.
        """

        data = [
            {'timestamp': testdata.t0, 'counter_volume': 12},
            {'timestamp': testdata.t0_10, 'counter_volume': 3},
            {'timestamp': testdata.t0_20, 'counter_volume': 7},
            {'timestamp': testdata.t0_30, 'counter_volume': 3},
            {'timestamp': testdata.t0_40, 'counter_volume': 25},
            {'timestamp': testdata.t0_50, 'counter_volume': 2},
            {'timestamp': testdata.t1, 'counter_volume': 6},
        ]

        xform = transformers.GaugeMax()
        usage = xform.transform_usage('some_meter', self.make_sample(data), TimeLabel(testdata.t0))

        self.assertEqual(usage[0].volume, 25)

    def test_all_same_values(self):
        """
        Tests that that transformer correctly grabs any value,
        when all values are the same.
        """

        data = [
            {'timestamp': testdata.t0, 'counter_volume': 25},
            {'timestamp': testdata.t0_30, 'counter_volume': 25},
            {'timestamp': testdata.t1, 'counter_volume': 25},
        ]

        xform = transformers.GaugeMax()
        usage = xform.transform_usage('some_meter', self.make_sample(data), TimeLabel(testdata.t0))

        self.assertEqual(usage[0].volume, 25)


class GaugeSumTransformerTests(BaseTransformTest):
    def test_basic_sum(self):
        """
        Tests that the transformer correctly calculate the sum value.
        """

        data = [
            {'timestamp': p('2015-01-01T00:00:00'), 'counter_volume': 1},
            {'timestamp': p('2015-01-01T00:10:00'), 'counter_volume': 1},
            {'timestamp': p('2015-01-01T01:00:00'), 'counter_volume': 1},
        ]

        xform = transformers.GaugeSum()
        usage = xform.transform_usage('fake_meter', self.make_sample(data), TimeLabel(testdata.t0))

        self.assertEqual(usage[0].volume, 2)


class FromImageTransformerTests(BaseTransformTest):
    """
    These tests rely on config settings for from_image,
    as defined in test constants, or in fitter.yaml
    """

    def test_from_volume_case(self):
        """
        If instance is booted from volume transformer should return none.
        """
        data = [
            {'timestamp': testdata.t0,
                'metadata': {'image_ref': ""}},
            {'timestamp': testdata.t0_30,
                'metadata': {'image_ref': "None"}},
            {'timestamp': testdata.t1,
                'metadata': {'image_ref': "None"}}
        ]

        data2 = [
            {'timestamp': testdata.t0_30,
                'metadata': {'image_ref': "None"}}
        ]

        xform = transformers.FromImage()
        usage = xform.transform_usage('instance', self.make_sample(data), TimeLabel(testdata.t0))
        usage2 = xform.transform_usage('instance', self.make_sample(data2), TimeLabel(testdata.t0))

        self.assertEqual([], usage)
        self.assertEqual([], usage2)

    def test_default_to_from_volume_case(self):
        """
        Unless all image refs contain something, assume booted from volume.
        """
        data = [
            {'timestamp': testdata.t0,
                'metadata': {'image_ref': ""}},
            {'timestamp': testdata.t0_30,
                'metadata': {'image_ref': "d5a4f118023928195f4ef"}},
            {'timestamp': testdata.t1,
                'metadata': {'image_ref': "None"}}
        ]

        xform = transformers.FromImage()
        usage = xform.transform_usage('instance', [OldSample(None, event) for event in data], TimeLabel(testdata.t0))

        self.assertEqual([], usage)

    def test_from_image_case(self):
        """
        If all image refs contain something, should return entry.
        """
        data = [
            {'timestamp': testdata.t0,
                'metadata': {'image_ref': "d5a4f118023928195f4ef", 'root_gb': "20"}},
            {'timestamp': testdata.t0_30,
                'metadata': {'image_ref': "d5a4f118023928195f4ef", 'root_gb': "20"}},
            {'timestamp': testdata.t1,
                'metadata': {'image_ref': "d5a4f118023928195f4ef", 'root_gb': "20"}}
        ]

        xform = transformers.FromImage()
        usage = xform.transform_usage('instance', self.make_sample(data), TimeLabel(testdata.t0))

        self.assertEqual(usage[0].end - usage[0].start, datetime.timedelta(hours=1, seconds=-1))

    def test_from_image_case_highest_size(self):
        """
        If all image refs contain something,
        should return entry with highest size from data.
        """
        data = [
            {'timestamp': testdata.t0,
                'metadata': {'image_ref': "d5a4f118023928195f4ef", 'root_gb': "20"}},
            {'timestamp': testdata.t0_30,
                'metadata': {'image_ref': "d5a4f118023928195f4ef", 'root_gb': "60"}},
            {'timestamp': testdata.t1,
                'metadata': {'image_ref': "d5a4f118023928195f4ef", 'root_gb': "20"}}
        ]

        xform = transformers.FromImage()
        usage = xform.transform_usage('instance', self.make_sample(data), TimeLabel(testdata.t0))

        self.assertEqual(usage[0].end - usage[0].start, datetime.timedelta(hours=1, seconds=-1))


class GaugeNetworkServiceTransformerTests(BaseTransformTest):

        def test_basic_sum(self):
            """Tests that the transformer correctly calculate the sum value.
            """

            data = [
                {'timestamp': p('2015-01-01T00:00:00'), 'counter_volume': 1},
                {'timestamp': p('2015-01-01T00:10:00'), 'counter_volume': 0},
                {'timestamp': p('2015-01-01T01:00:00'), 'counter_volume': 2},
            ]

            xform = transformers.GaugeNetworkService()
            usage = xform.transform_usage('fake_meter', self.make_sample(data), TimeLabel(testdata.t0))

            self.assertEqual(usage[0].end - usage[0].start, datetime.timedelta(hours=1, seconds=-1))
