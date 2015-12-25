import binascii
import conf
import errors
import logbook
from memdb import MemDbModel, create_redis_client
from os import urandom
from collections import namedtuple


def random_id(bytes_count):
    """ Returns secure random string
    """
    raw = urandom(bytes_count)
    return binascii.hexlify(raw).decode("ascii")


class BaseToken(MemDbModel):
    """
    Base Model of tokens.

    """

    _key_prefix = None
    config = None
    invalid_token = None
    Token = namedtuple("Token", ["id"])

    _redis_client = None

    @classmethod
    def redis(cls):
        if not cls._redis_client:
            db_index = cls.config.get("db_index", None)
            cls._redis_client = create_redis_client(db_index)
        return cls._redis_client

    @classmethod
    def generate_random_id(cls, bytes_count=None):
        return random_id(bytes_count or cls.config.size)

    @classmethod
    def generate(cls, model=None):
        return cls.generate_random_id()

    @classmethod
    def serialize(cls, token):
        # noinspection PyProtectedMember
        return token._asdict()

    @classmethod
    def deserialize(cls, data):
        data = {k.decode("ascii"): v.decode("ascii") for k, v in data.items()}
        return data

    @classmethod
    def save(cls, token):
        key = cls.prefixed_key(token.id)
        ttl = cls.config.ttl
        cls.redis().hmset(key, cls.serialize(token))
        cls.redis().expire(key, ttl)
        return token

    # noinspection PyCallingNonCallable
    @classmethod
    def get(cls, token_id):
        key = cls.prefixed_key(token_id)
        data = cls.redis().hgetall(key)
        if not data:
            logbook.debug("Token {} not found in memdb {}", cls.__name__, key)
            raise cls.invalid_token()
        try:
            data = {k.decode("ascii"): v.decode("ascii") for k, v in data.items()}
            return cls.Token(**data)
        except TypeError:
            logbook.exception()
            raise cls.invalid_token()

    @classmethod
    def remove(cls, token):
        key = cls.prefixed_key(token.id)
        cls.redis().delete(key)

    @classmethod
    def create(cls, model):
        token_id = cls.generate(model)
        token_data = {"id": token_id}
        for field_name in cls.Token._fields:
            if field_name != "id":
                token_data[field_name] = str(getattr(model, field_name))
        token = cls.Token(**token_data)
        # noinspection PyTypeChecker
        cls.save(token)
        return token


class BaseScannableToken(BaseToken):
    second_index = ""

    @classmethod
    def generate(cls, model=None):
        assert model
        second_index = str(getattr(model, cls.second_index))
        return cls._key_join_symbol.join([second_index, cls.generate_random_id()])

    @classmethod
    def update_by(cls, second_index, **kwargs):
        keys = cls._find_keys_by(second_index)
        if not keys:
            return
        with cls.redis().pipeline(transaction=False) as p:
            for key in keys:
                p.hmset(key, kwargs)
            p.execute()

    @classmethod
    def find_by(cls, second_index):
        return [cls(key.lstrip(cls._key_prefix)) for key in cls._find_keys_by(second_index)]

    @classmethod
    def _find_keys_by(cls, second_index):
        return cls.redis().keys(cls.prefixed_key(str(second_index), "*"))

    @classmethod
    def remove_by(cls, second_index):
        keys = cls._find_keys_by(second_index)
        if keys:
            return cls.redis().delete(*keys)


class UserToken(BaseScannableToken):
    _key_prefix = "ut-"
    config = conf.user.token
    invalid_token = errors.UserInvalidToken
    Token = namedtuple('UserToken', ['id', 'user_id', 'role', 'email'])
    second_index = "user_id"


class CustomerToken(BaseScannableToken):
    _key_prefix = "ct-"
    config = conf.customer.token
    invalid_token = errors.CustomerInvalidToken
    Token = namedtuple('CustomerToken', ['id', 'customer_id', 'email', 'role'])
    second_index = "customer_id"


class PasswordResetToken(BaseToken):
    _key_prefix = "u-password-reset"
    config = conf.user.password_token
    invalid_token = errors.PasswordResetTokenInvalid
    Token = namedtuple('PasswordToken', ['id', 'user_id'])


class CustomerPasswordResetToken(BaseToken):
    _key_prefix = "c-password-reset"
    config = conf.customer.password_token
    invalid_token = errors.PasswordResetTokenInvalid
    Token = namedtuple('CustomerPasswordToken', ['id', 'customer_id'])


class EmailConfirmationToken(BaseToken):
    _key_prefix = "c-email-confirmation"
    config = conf.customer.email_confirmation_token
    invalid_token = errors.EmailConfirmationTokenInvalid
    Token = namedtuple('PasswordToken', ['id', 'customer_id'])
