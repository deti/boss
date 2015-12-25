# -*- coding: utf-8 -*-
import math
from decimal import Decimal


def to_gigabytes_from_bytes(value):
    """From Bytes, unrounded."""
    return ((value / Decimal(1024)) / Decimal(1024)) / Decimal(1024)

def to_bytes_from_gigabytes(value):
    return value * 1073741824


def to_hours_from_seconds(value):
    """From seconds to rounded hours"""
    return Decimal(math.ceil((value / Decimal(60)) / Decimal(60)))


conversions = {
    'byte': {'gigabyte': to_gigabytes_from_bytes},
    'second': {'hour': to_hours_from_seconds},
    'GB': {'B': to_bytes_from_gigabytes}
}


def convert_to(value, from_unit, to_unit):
    """Converts a given value to the given unit.
       Assumes that the value is in the lowest unit form,
       of the given unit (seconds or bytes).
       e.g. if the unit is gigabyte we assume the value is in bytes"""
    if from_unit == to_unit:
        return value
    return conversions[from_unit][to_unit](value)
