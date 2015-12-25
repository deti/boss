# -*- coding: utf-8 -*-
"""
This module has a lightweight validation framework for API.

It is rather simple but provides you with all possibilities you might require from validation. It is
way more faster and simpler than WTForms.
"""


import collections
import functools
import inspect
import traceback

from bottle import request, HTTPError
from api import request_api_type, API_ADMIN, CABINET_TOKEN_NAME, ADMIN_TOKEN_NAME
from errors import BadRequest, BadParameter
from api.validator import ValidateError
import logbook
from utils.i18n import _


class ParameterType(object):
    """
    This class incapsulates metadata about parameter. It stores if parameter is mandatory and
    a list of validator and the name of the argument.
    """

    __slots__ = ("name", "required", "validators")

    # The name of the token argument. Token has special meaning so we have to distinguish it in another way
    TOKEN_NAME = "token"

    def __init__(self, name, types, all_args):
        """
        Constructor.

        :param str name: The name of the argument
        :param list types: The list of types (validators) which have to be applied to incoming parameter
        :param set all_args: The list of all arguments. This is required to check if parameter is mandatory or not.
        """
        self.name = name
        self.required = name in all_args
        self.validators = []
        if not isinstance(types, tuple):
            types = (types,)

        for type_ in types:
            self.validators.append(
                type_() if type(type_) is type else type_
            )

    def validate(self, value):
        """
        This method validates given value. It doesn't catch any exception, it is a task of internal executor.

        :param object value: The value we have to validate.
        :return Validated value.
        """
        processed_value = value
        for type_validator in self.validators:
            try:
                processed_value = type_validator(value)
            except ValidateError as exc:
                if self.name != self.TOKEN_NAME:
                    name = self.name
                    if exc.subname:
                        name += "." + exc.subname
                    raise BadParameter(exc, name)
                raise BadRequest(exc)
            except HTTPError as exc:
                raise exc
            except Exception as exc:
                logbook.info(u"Invalid parameter {}: {} ({})".format(self.name, exc, type(exc)))
                logbook.debug("{}", traceback.format_exc())
                if hasattr(type_validator, "__class__"):
                    validator_name = type_validator.__class__.__name__
                else:
                    validator_name = getattr(type_validator, "__name__", "<unknown type>")

                raise BadRequest(
                    _(u"Invalid parameter {}. It should have type {}"),
                    self.name, validator_name)
        return processed_value


class ParameterValidator(object):
    """
    Actual class which responsible for validation. Actually check_params decorator just puts everything in it
    and relies on it during the processing.
    """

    __slots__ = ("all_parameters", "function", "param_info", "args")

    @staticmethod
    def request_params():
        """
        Detects where do we have incoming arguments and returns them.

        :return tuple of parameters (dict-like structure) and sign were they JSONed or not. This is required
        if we have different rules for processing form-data and simple JSON.
        """
        try:
            params, is_json = request.json, True
        except ValueError:
            params, is_json = None, False
        if not params:
            params, is_json = request.params, False
        return params, is_json

    @staticmethod
    def extract_value(name, type_, default_params, incoming_params):
        """
        Extracts value from the incoming arguments and does some decoding if necessary. It does not validates,
        it just extracts.

        :param str name: The name of an argument you want to extracts
        :param ParameterType type_: Validator for the parameter (actually it does not validates, just put some
            internal logic for parameter requiring).
        :param dict default_params: Default parameters in case if something is absent
        :param dict incoming_params: Incoming parameters.
        :param bool is_json: This flags detects the reason of incoming_params. Were they extracted from JSON or not.

        :return Value.
        """
        if name == ParameterType.TOKEN_NAME:
            token_name = ADMIN_TOKEN_NAME if request_api_type() == API_ADMIN else CABINET_TOKEN_NAME
            return request.get_cookie(token_name) or ""

        value = incoming_params.get(name)
        if value is None:
            value = default_params.get(name)

        if value is None and type_.required:
            raise BadRequest(_(u"{} is required"), name)

        return value

    def __init__(self, function, all_parameters, **types):
        """
        Constructor.

        :param function function: The function we have to execute if validation succeed.
        :param bool all_parameters: Convenient hack. If we set this to True, then function will get another argument,
            "all_parameters" which is dictionary with a rest of arguments. In some cases this is rather convenient.
        :param dict types: The mappings between argument names and validators.
        """
        self.all_parameters = all_parameters
        self.function = function

        arg_spec = inspect.getargspec(get_real_function(function))
        defaults = arg_spec.defaults or []
        self.args = set(arg_spec.args[:len(arg_spec.args) - len(defaults)])
        param_info = [(param, ParameterType(param, param_type, self.args)) for param, param_type in types.items()]

        self.param_info = collections.OrderedDict(param_info)

    def process(self, *args, **kwargs):
        """
        This process arguments and returns result of function if everything is ok. Actually, this is the only
        method you want to execute.
        """
        validated_args, validated_kwargs = self.validate(*args, **kwargs)
        if self.all_parameters:
            validated_kwargs["all_parameters"] = validated_kwargs.copy()
            validated_kwargs["all_parameters"].pop(ParameterType.TOKEN_NAME, "")
        return self.function(*validated_args, **validated_kwargs)

    def validate(self, *args, **kwargs):
        """
        Validates incoming arguments. Do not use it as is, use `process` method instead.
        """
        validated_args = args
        validated_kwargs = {}
        request_params, is_json = self.request_params()

        def fix_encode(value):
            try:
                return value.encode('latin1').decode("utf-8")
            except UnicodeDecodeError:
                raise BadRequest(_("Invalid encoding: %s") %
                                 value.encode("ascii", "backslashreplace").decode("ascii"))

        if is_json:
            parameters = request_params
        else:
            parameters = {fix_encode(k): fix_encode(v) for k, v in request_params.items()}
        request.parameters = parameters

        for name, type_ in self.param_info.items():
            value = self.extract_value(name, type_, kwargs, parameters)
            if value is None:
                continue
            if name == ParameterType.TOKEN_NAME and ParameterType.TOKEN_NAME not in self.args:
                type_.validate(value)
            else:
                validated_kwargs[name] = type_.validate(value)

        return validated_args, validated_kwargs


def check_params(all_parameters=False, **types):
    """
    Decorator for validating input.

    :param bool all_parameters: If we set this to True, then function will get another argument,
        "all_parameters" which is dictionary with a rest of arguments. In some cases this is rather convenient.
    :param dict types: Mapping between validators and argument names.

    :return The result of function call.
    """
    def outer_decorator(func):
        function_validator = ParameterValidator(func, all_parameters, **types)

        @functools.wraps(func)
        def inner_decorator(*args, **kwargs):
            return function_validator.process(*args, **kwargs)

        inner_decorator.__wrapped__ = func
        return inner_decorator
    return outer_decorator


def get_real_function(function):
    """
    Unwraps decorated function to get the real one.

    Wrappers should set ``__wrapped__`` attribute with original function.
    """
    real_function = function
    while hasattr(real_function, "__wrapped__"):
        real_function = real_function.__wrapped__
    return real_function
