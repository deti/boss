import conf
import errors
from decimal import Decimal, DecimalException, getcontext
from babel.numbers import format_decimal

_precision = Decimal(conf.backend.decimal.money_precision)


def string_to_money(value, precision=_precision):
    """
    Convert string like "12.34" to int with fixed point. The precision (scale factor) is set in config files.
    By default precision is 0.01, i.e. "12.34" will be converted to 1234.
    """
    assert isinstance(value, str)
    try:
        return int(decimal_to_money(Decimal(value), precision))
    except DecimalException:
        raise errors.InvalidMoney()


def money_to_string(value, precision=_precision):
    """
    Convert int with fixed point to string. The precision (scale factor) is set in config files.
    By default precision is 0.01, i.e. 1234 will be converted to "12.34"

    """
    assert isinstance(value, int)
    return str((Decimal(value) * precision).quantize(precision))


def money_dict_to_string(d):
    return {key: money_to_string(value) for key, value in d.iteritems()}


def money_to_decimal(value, precision=_precision):
    """
    Convert int with fixed point to decimal type.
    """
    assert isinstance(value, int)
    return Decimal(value) * precision


def decimal_to_money(value, precision=_precision):
    """
    Convert decimal to int with fixed point.
    """
    return int(value.quantize(precision) / precision)


def string_to_decimal(value, precision=_precision):
    """
    Convert string to decimal.
    """
    assert isinstance(value, str)
    return Decimal(value).quantize(precision)


def decimal_to_string(value, precision=_precision, locale=None, number_format="#.##"):
    """
    Convert decimal to string
    """
    assert isinstance(value, Decimal)
    if locale is None:
        return str(value.quantize(precision))

    return format_decimal(value.quantize(precision), locale=locale, format=number_format)


def max_money():
    """
    Return max money which can be represented by int with fixed point
    """
    return 10 ** getcontext().prec - 1
