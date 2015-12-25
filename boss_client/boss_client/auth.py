# -*- coding: utf-8 -*-
import hashlib
import hmac
import time
import requests.auth
import logbook
from hmac import compare_digest
from urllib.parse import urlsplit, unquote


class AuthError(Exception):
    """
    Base class of auth errors
    """

    def __init__(self, message, *args):
        message = message % args
        super(AuthError, self).__init__(message)

        self.message = message

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, self.message)


class NoHeaderError(AuthError):
    """
    This class defines error when no Authorization header is found.
    """

    pass


class LengthError(AuthError):
    """
    This class defines error when Authorization header does not suit length conditions.
    """

    pass


class TimestampError(AuthError):
    """
    This class defines error when no suitable timestamp is found.
    """

    pass


class IncorrectSignatureError(AuthError):
    """
    This class defines error when signature is incorrect.
    """

    pass


class Signature(object):
    ALGORITHM = hashlib.sha256

    # The length of a signature
    SIGNATURE_LENGTH = len(ALGORITHM(b"").hexdigest())

    def __init__(self, secret_key, timestamp_range=30):
        self.secret_key = secret_key
        self.timestamp_range = timestamp_range

    def canonical_parameters(self, parameters):
        def encode(value):
            if isinstance(value, bytes):
                return value
            if isinstance(value, int):
                value = str(value)
            elif isinstance(value, dict):
                return self.canonical_parameters(value)
            elif isinstance(value, list):
                return b"".join(encode(v) for v in value)
            if isinstance(value, str):
                return value.encode("utf-8")
            raise Exception("Invalid type %s of value %s" % (type(value), value))

        params = sorted(encode(key) + b'=' + encode(value) for key, value in parameters.items())
        return b'&'.join(params)

    def canonical_str(self, timestamp, method, path, parameters):
        parts = [part.encode("utf-8") for part in (timestamp, method.upper(), path)]
        parts.append(self.canonical_parameters(parameters))

        signature = b"\n".join(parts)
        return signature

    def calculate_signature(self, timestamp, method, path, parameters):
        timestamp = str(int(timestamp))
        canonical_str = self.canonical_str(timestamp, method, path, parameters)
        logbook.debug("Canonical string is {}", canonical_str)

        signature = hmac.new(self.secret_key.encode("utf-8"), canonical_str, self.ALGORITHM).hexdigest()
        logbook.debug("Signature: {}", signature)

        return signature + timestamp

    def extract_signature(self, signature_str):
        """
        This function extracts signature from Authorization header.

        Returns None if no signature is available.
        """

        if len(signature_str) > self.SIGNATURE_LENGTH:
            return signature_str[:self.SIGNATURE_LENGTH]

        return None

    def extract_timestamp(self, signature_str):
        """
        This function extracts timestamp from Authorization header.

        Returns None if no timestamp is available.
        """

        if len(signature_str) > self.SIGNATURE_LENGTH:
            timestamp = signature_str[self.SIGNATURE_LENGTH:]
            if timestamp.isdigit():
                return int(timestamp)

        return None

    def verify(self, auth_str, method, path, parameters):
        """Verifies that given params have expected signature."""

        if len(auth_str) <= self.SIGNATURE_LENGTH:
            raise LengthError("The length of authorization header %s is %d. Expected at least %d characters",
                              auth_str, len(auth_str), self.SIGNATURE_LENGTH)

        timestamp = self.extract_timestamp(auth_str)
        if not timestamp:
            raise TimestampError("Impossible extract timestamp from authorization header %s", auth_str)

        now = int(time.time())
        if timestamp > now + 1 or timestamp < now - self.timestamp_range:
            raise TimestampError("Timestamp %s is too old or from future. now is %s", timestamp, now)

        calculated_auth = self.calculate_signature(timestamp=timestamp,
                                                   method=method,
                                                   path=path,
                                                   parameters=parameters)

        if not compare_digest(auth_str, calculated_auth):
            raise IncorrectSignatureError("Calculated signature %s mismatch expected %s", calculated_auth, auth_str)

    def verify_requests(self, auth_str, request, parameters):
        """Verifies that requests.Request has proper signature."""

        try:
            self.verify(auth_str, request.method, request.path, parameters)
        except AuthError:
            return False

        return True


class HMACAuth(requests.auth.AuthBase):
    """
    This class provides HMAC authentication for BillingAPIClient.
    """
    HEADER_NAME = "Authorization"

    def __init__(self, secret_key):
        super(HMACAuth, self).__init__()
        self.signature = Signature(secret_key)

    def __call__(self, request):
        path = urlsplit(request.url).path
        path = unquote(path)

        request.headers[self.HEADER_NAME] = self.signature.calculate_signature(
            timestamp=time.time(),
            method=request.method,
            path=path,
            parameters=parameters
        )

        return request
