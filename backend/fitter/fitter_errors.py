# -*- coding: utf-8 -*-


class FitterBaseException(BaseException):
    pass


class NotFound(FitterBaseException):
    pass


class TenantNotFound(FitterBaseException):
    pass


class TenantNameInvalid(FitterBaseException):
    pass


class TenantIdInvalid(FitterBaseException):
    pass


class InvalidDateFormat(FitterBaseException):
    pass