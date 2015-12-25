# -*- coding: utf-8 -*-
import conf
import errors
import pytz
import logbook
import json
from datetime import datetime
from re import compile as regex_compile, IGNORECASE
from abc import ABCMeta
from decimal import getcontext, Context, Decimal as BaseDecimal
from babel import Locale as BabelLocale, UnknownLocaleError
from utils.i18n import _, DEFAULT_LANGUAGE, available_languages
from arrow import utcnow
from itertools import chain
from model.account.customer import Customer

JSONDecodeError = ValueError


class ValidateError(errors.ErrorWithFormattedMessage):
    subname = None


class JSON (object):
    NOT_JSON = object()

    @staticmethod
    def to_json(value):
        # this is to support both form-encoded and post json
        if isinstance(value, str):
            try:
                return json.loads(value)
            except JSONDecodeError:
                pass

        return JSON.NOT_JSON

    @staticmethod
    def construct_validator(reference_scheme):
        def validator(element, scheme=reference_scheme):
            if callable(scheme):
                return scheme(element)

            elif isinstance(scheme, tuple):
                for type_validator in scheme:
                    return validator(element, type_validator)

            elif isinstance(element, list):
                if isinstance(scheme, list):
                    assert scheme
                    return [validator(part, scheme[0]) for part in element]

            elif isinstance(element, dict):
                if isinstance(scheme, dict):
                    assert scheme
                    try:
                        dct = {}
                        for key, value in scheme.items():
                            if key not in element:
                                if value is None or isinstance(value, tuple) and None in value:
                                    continue
                                else:
                                    raise ValidateError(_("Field {} is required"), key)
                            if element[key] is None:
                                dct[key] = None
                            else:
                                try:
                                    dct[key] = validator(element[key], value)
                                except ValidateError as exc:
                                    error = ValidateError(str(exc))
                                    error.subname = key
                                    raise error
                        return dct
                    except KeyError:
                        pass

            elif scheme is str:
                if isinstance(element, str):
                    return element

            elif scheme in (int, float):
                if isinstance(element, scheme):
                    return element

            elif element == scheme:
                return element

            raise ValidateError(_("Unexpected element {}"), repr(element))

        return validator

    def __call__(self, value):
        result = self.to_json(value)
        if result is self.NOT_JSON:
            raise ValidateError(_("Cannot decode JSON {}"), str(value))

        return result


class List(object):

    DEFAULT_STRING_DELIMITER = ','

    def __init__(self, item_validator=None, string_delimiter=None):
        if item_validator is None:
            item_validator = lambda element: element
        if string_delimiter is None:
            string_delimiter = self.DEFAULT_STRING_DELIMITER
        self.validator = item_validator
        self.delimiter = string_delimiter

    def __call__(self, value):
        original_value = value
        if isinstance(value, str):
            j = JSON.to_json(value)
            if j is JSON.NOT_JSON or not isinstance(j, list):
                value = value.split(self.delimiter)
            else:
                value = j

        if not isinstance(value, list):
            logbook.info("Value '{}' can't be decoded as json list, or delimiter list (delimiter '{}')",
                         original_value, self.delimiter)
            raise ValidateError(_('list is expected'))

        return [self.validator(element) for element in value]


class JSONList (List):

    def __init__(self, element_scheme, string_delimiter=None):
        validator = JSON.construct_validator(element_scheme)
        super(JSONList, self).__init__(validator, string_delimiter)


class Dict(object):
    def __call__(self, value):
        if isinstance(value, str):
            value = JSON.to_json(value)
        if not isinstance(value, dict):
            raise ValidateError(_("should be a dict"))
        return value


class IntRange(object):

    def __init__(self, min_=None, max_=None):
        self.min = min_
        self.max = max_

    def __call__(self, value):
        try:
            value = int(value)
        except ValueError:
            raise ValidateError(_('{} should be integer'), str(value))

        if self.min is not None and value < self.min:
            raise ValidateError(_("Value should be greater than {}"), self.min)
        if self.max is not None and value > self.max:
            raise ValidateError(_("Value should be less than {}"), self.max)

        return value


class SingleSort(object):

    def __init__(self, fields=None):
        self.fields = fields

    def __call__(self, field):
        order = 1
        if field.startswith("-"):
            order = -1
            field = field[1:]
        if self.fields:
            if field not in self.fields:
                raise ValidateError(
                    _("Invalid format. Expected '[-]field_name', where field_name one of: {}"),
                    self.fields
                )

        return field, order


class Sort(List):
    def __init__(self, fields=None):
        super(Sort, self).__init__(SingleSort(fields))


class DateTime(metaclass=ABCMeta):

    UNDIVIDED_TPL = None
    UNDIVIDED_LEN = None

    DIVIDED_TPL = None
    DIVIDED_LEN = None

    def undivided(self, timestamp):
        assert hasattr(self, "UNDIVIDED_TPL") and hasattr(self, "UNDIVIDED_LEN")
        if len(timestamp) != self.UNDIVIDED_LEN:
            raise ValueError
        return datetime.strptime(timestamp, self.UNDIVIDED_TPL)

    def divided(self, timestamp):
        assert hasattr(self, "DIVIDED_TPL") and hasattr(self, "DIVIDED_LEN")
        if len(timestamp) != self.DIVIDED_LEN:
            raise ValueError
        return datetime.strptime(timestamp, self.DIVIDED_TPL)

    def unix(self, timestamp):
        try:
            return datetime.utcfromtimestamp(int(timestamp))
        except Exception as e:
            logbook.info("Invalid timestamp: {}", timestamp)
            raise ValueError()

    def __call__(self, value):
        value = value.strip()
        for func in (self.undivided, self.divided, self.unix):
            try:
                return func(value)
            except ValueError:
                pass


class Day(DateTime):

    UNDIVIDED_TPL = "%Y%m%d"
    UNDIVIDED_LEN = len("20130128")

    DIVIDED_TPL = "%Y-%m-%d"
    DIVIDED_LEN = len("2013-01-28")

    def unix(self, timestamp):
        day = super(Day, self).unix(timestamp)
        is_day = (
            day.minute == 0 and
            day.hour == 0 and
            day.second == 0 and
            day.microsecond == 0
        )
        if not is_day:
            raise ValueError

        return day

    def __call__(self, value):
        result = super(Day, self).__call__(value)
        if not result:
            raise ValidateError(_(u"Incorrect day format"))

        return result.date()


class Date(DateTime):

    UNDIVIDED_TPL = "%Y%m%d%H%M%S"
    UNDIVIDED_LEN = len("20130128003712")

    DIVIDED_TPL = "%Y-%m-%dT%H:%M:%S"
    DIVIDED_LEN = len("2013-01-28T00:37:12")

    UTC_TZ = pytz.utc

    def __call__(self, value):
        result = super(Date, self).__call__(value)
        if not result:
            raise ValidateError(_("Incorrect date format"))

        return result.replace(tzinfo=self.UTC_TZ)


class DeferredDate (Date):
    def __call__(self, value):
        result = super(DeferredDate, self).__call__(value)
        if result < utcnow().datetime:
            raise ValidateError(_("Date expired"))
        return result


class Time (object):

    TIME_REGEXP = regex_compile(r"^(?P<hours>20|21|22|23|[01]\d|\d)([:.](?P<minutes>[0-5]\d))$")

    def __call__(self, value):
        matcher = Time.TIME_REGEXP.match(value)
        if not matcher:
            raise ValidateError(_("Incorrect time format"))

        matcher = matcher.groupdict()

        return 3600 * int(matcher["hours"]) + 60 * int(matcher["minutes"])


class Choose (object):

    def __init__(self, values, case_insensitive=True):
        assert isinstance(values, (dict, list, tuple, set, frozenset))

        if case_insensitive:
            self.fix_case = lambda key: key.lower() if isinstance(key, str) else key
        else:
            self.fix_case = lambda key: key

        if isinstance(values, dict):
            iterator = values.items()
        else:
            iterator = ((value, value) for value in values)

        self.values = dict((self.fix_case(key), value) for key, value in iterator)
        self.case_insensitive = case_insensitive

    def __call__(self, value):
        value = self.fix_case(value)
        if value not in self.values:
            raise ValidateError(
                _(u"value should one from list: {}"),
                u",".join(map(str, self.values.keys()))
            )
        return self.values[value]


class PredefinedChoose (Choose):

    def __init__(self, case_insensitive=True):
        assert hasattr(self, 'FIELDS')
        # noinspection PyUnresolvedReferences
        super(PredefinedChoose, self).__init__(self.FIELDS, case_insensitive)


class ChooseOrEmpty (Choose):

    def __init__(self, values, case_insensitive=True):
        super(ChooseOrEmpty, self).__init__(list(values) + [""], case_insensitive)


class Bool (PredefinedChoose):

    BOOL_MATCH = {
        True: ["yes", "1", 1, "on", "true", True],
        False: ["no", "0", 0, "off", "false", False]
    }

    def __init__(self, case_insensitive=True):
        self.FIELDS = {}
        for key, values in self.BOOL_MATCH.items():
            self.FIELDS.update((value, key) for value in values)
        super(Bool, self).__init__(case_insensitive)


class ForceUpdate (Bool):

    def __call__(self, value):
        if not conf.devel.force_update_allowed:
            return False
        return super(ForceUpdate, self).__call__(value)


class FilterMode (PredefinedChoose):
    FIELDS = ("exact", "regexp", "contain", "start", "startCI", "regexpCI", "containCI")


class HighlightType (PredefinedChoose):
    FIELDS = ("clips", "cuts")


class Email (object):

    USER_REGEX = regex_compile(
        r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*$"  # dot-atom
        r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-\011\013\014\016-\177])*"$)',  # quoted-string
        IGNORECASE
    )
    DOMAIN_REGEX = regex_compile(
        r'(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?$)'  # domain
        # literal form, ipv4 address (SMTP 4.1.3)
        r'|^\[(25[0-5]|2[0-4]\d|[0-1]?\d?\d)(\.(25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3}\]$',
        IGNORECASE
    )
    DOMAIN_WHITELIST = ["localhost"]

    def __call__(self, value):
        if not value or '@' not in value:
            raise ValidateError(_(u"Email must include @ symbol"))

        user_part, domain_part = value.rsplit('@', 1)

        if not self.USER_REGEX.match(user_part):
            raise ValidateError(_(u"mail box in email is incorrect"))

        if domain_part not in self.DOMAIN_WHITELIST and not self.DOMAIN_REGEX.match(domain_part):
            # Try for possible IDN domain-part
            try:
                domain_part = domain_part.encode('idna').decode('ascii')
                if not self.DOMAIN_REGEX.match(domain_part):
                    raise ValidateError(_(u"Domain part of email is incorrect"))
                else:
                    return value
            except UnicodeError:
                pass

            raise ValidateError(_(u"Domain part of email is incorrect"))

        return value


class EmailOrEmpty(Email):
    def __call__(self, value):
        if not value:
            return value
        return super(EmailOrEmpty, self).__call__(value)


class Money (object):

    MONEY_REGEXP = regex_compile(r"^[+-]?\d+(\.\d{1,2})?$")

    def __init__(self, positive_only=False, negative_only=False):
        assert not (positive_only and negative_only), "Wrong validator configuration"
        self.positive_only = positive_only
        self.negative_only = negative_only

    def __call__(self, value):
        if isinstance(value, str) and self.MONEY_REGEXP.match(value):
            if self.positive_only and value.startswith("-"):
                raise ValidateError(_("Amount should be positive"))
            elif self.negative_only and not value.startswith("-"):
                raise ValidateError(_("Amount should be negative"))
            return value

        raise ValidateError(_("Money format is xx.xx"))


class DecimalMoney(Money):
    def __call__(self, value):
        value = super().__call__(value)
        value = BaseDecimal(value)
        return value


class EmailList (List):

    def __init__(self, string_delimiter=None):
        super(EmailList, self).__init__(Email(), string_delimiter)


class Locale (object):

    def __call__(self, value):
        normalized_value = value.replace(u"-", u"_")
        try:
            BabelLocale.parse(normalized_value)
            return normalized_value
        except (ValueError, UnknownLocaleError):
            raise ValidateError(_(u"Incorrect locale {}"), value)


class Language (Locale):

    def __call__(self, value):
        locale = super(Language, self).__call__(value)
        return BabelLocale.parse(locale).language


class ActiveLanguage(Language):
    def __call__(self, value):
        language = super().__call__(value)
        if language not in available_languages():
            raise ValidateError(_(u"Language {} is not active"), value)
        return language


class ActiveLocale (Locale):
    def __call__(self, value):
        locale = super(ActiveLocale, self).__call__(value)
        ActiveLanguage()(locale)
        return locale

class BaseTokenId:
    LOCAL_PROPERTIES = None
    TOKEN = None

    def __call__(self, value):
        if not value:
            logbook.debug("Token {} is not sent", self.TOKEN.__name__)
            raise self.TOKEN.invalid_token()

        if self.LOCAL_PROPERTIES is None:
            from api import local_properties
            self.LOCAL_PROPERTIES = local_properties

        token = self.TOKEN.get(value)

        self.LOCAL_PROPERTIES.user_token = token
        return token


from memdb.token import UserToken, CustomerToken

class TokenId(BaseTokenId):
    TOKEN = UserToken


class CustomerTokenId(BaseTokenId):
    TOKEN = CustomerToken


class String(object):
    def __call__(self, value):
        return str(value)


class StringWithLimits(object):

    def __init__(self, min_length=0, max_length=conf.api.max_parameter_length):
        self.min_length = min_length
        self.max_length = max_length

    def __call__(self, value):
        value = str(value)
        length = len(value)
        if length > self.max_length or length < self.min_length:
            raise ValidateError(_(u"string length must be between {} and {}"), self.min_length, self.max_length)
        return value


IndexSizeLimit = StringWithLimits(max_length=conf.database_limits.index_key_limit)


class Integer(object):
    MAX_8_BYTES_SIGNED_INTEGER = 2 ** 63

    def __call__(self, value):
        try:
            value = int(value)
        except (ValueError, TypeError):
            raise ValidateError(_(u"Value should be int"))
        if abs(value) > self.MAX_8_BYTES_SIGNED_INTEGER:
            raise ValidateError(_(u"Value should be smaller than {}"), self.MAX_8_BYTES_SIGNED_INTEGER)
        return value


class PositiveInteger(Integer):
    def __call__(self, value):
        value = super().__call__(value)
        if value < 0:
            raise ValidateError(_(u"{} should be positive integer"), value)
        return value


class ModelId(PositiveInteger):
    def __init__(self, model=None, error=errors.NotFound, expand=True):
        self.model = model
        self.error = error
        self.expand = expand

    def __call__(self, value):
        value = super().__call__(value)
        if self.model:
            obj = self.model.get_by_id(value)
            if not obj:
                raise self.error()
            if self.expand:
                value = obj
        return value


class LongInteger(object):
    def __call__(self, value):
        return int(value)


class Float(object):
    def __call__(self, value):
        return float(value)


class PositiveFloat(Float):
    def __call__(self, value):
        value = float(value)
        if value < 0:
            raise ValidateError(_(u"{} should be positive float"), value)
        return value


class Decimal(object):

    def __init__(self, **kwargs):
        if not kwargs:
            self.context = getcontext()
        else:
            self.context = Context(**kwargs)

    def __call__(self, value):
        return BaseDecimal(value, self.context)

    def normalize_fraction(self, value):
        decimal = BaseDecimal(value, self.context)
        normalized = decimal.normalize()
        sign, digits, exponent = normalized.as_tuple()
        if exponent > 0:
            return BaseDecimal((sign, digits + (0,) * exponent, 0), self.context)
        else:
            return normalized


class Regexp(object):
    def __init__(self, regexp, flags=0):
        if isinstance(regexp, str):
            self.regexp = regex_compile(regexp, flags)
        else:
            self.regexp = regexp

    def __call__(self, value):
        if not self.regexp.match(value):
            raise ValidateError(_(u"should match regex: {}"), self.regexp.pattern)
        return value


class LocalizedName(JSON):
    KEY_VALIDATOR = ActiveLanguage()
    VALUE_VALIDATOR = StringWithLimits(max_length=254)

    def __init__(self, requires_default_language=True):
        super().__init__()
        self.requires_default_language = requires_default_language

    def __call__(self, value):
        if isinstance(value, str):
            parsed_value = super().__call__(value)
        else:
            parsed_value = value

        if not isinstance(parsed_value, dict):
            raise ValidateError(_(u"{} has to be a dictionary"), value)

        result = {
            self.KEY_VALIDATOR(key): self.VALUE_VALIDATOR(value) for key, value in parsed_value.items()
        }
        if self.requires_default_language and DEFAULT_LANGUAGE not in result:
            raise errors.HasToHaveDefinedNameInDefaultLanguage()
        return result


class Visibility(Choose):

    VISIBLE = "visible"
    DELETED = "deleted"
    ALL = "all"
    DEFAULT = VISIBLE

    def __init__(self):
        super(Visibility, self).__init__([self.ALL, self.VISIBLE, self.DELETED, "", None], case_insensitive=True)

    def __call__(self, value):
        value = super(Visibility, self).__call__(value)
        if not value:
            return self.DEFAULT
        return value


class SecretSign(object):
    def __init__(self, name, secret=None):
        from boss_client.auth import Signature
        self.name = name
        self.signature = Signature(secret or conf.api.secure.secret_key)

    def __call__(self, value):
        import bottle
        if not value:
            return None
        parameters = bottle.request.parameters.copy()
        parameters.pop(self.name)
        return self.signature.verify_requests(value, bottle.request, parameters)


class SortFields(Choose):

    def __init__(self, model):
        fields = model.sorting_fields or model.display_fields
        super().__init__(list(chain.from_iterable((field, '-' + field) for field in fields)))

