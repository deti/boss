import conf
import errors
import logbook
from model import db, AccountDb, duplicate_handle
from sqlalchemy import Column
from memdb.token import UserToken
# noinspection PyUnresolvedReferences
from passlib.hash import pbkdf2_sha256
from arrow import utcnow
from model.account.role import Role


class User(db.Model, AccountDb):
    id_field = "user_id"
    unique_field = "email"

    user_id = Column(db.Integer, primary_key=True)
    email = Column(db.String(254), nullable=False, unique=True)
    password = Column(db.String(100), nullable=False)
    role = Column(db.String(16), nullable=False)
    name = Column(db.String(256))
    deleted = Column(db.DateTime())
    created = Column(db.DateTime())

    display_fields = frozenset(("user_id", "email", "role", "name", "created", "deleted"))
    display_fields_short = frozenset(("user_id", "name"))
    extract_fields = {"role": Role.display}

    def __str__(self):
        return "<User {0.email} ({0.role})>".format(self)

    @classmethod
    def password_hashing(cls, raw_password):
        return pbkdf2_sha256.encrypt(raw_password, rounds=conf.user.salt_rounds, salt_size=10)

    def check_password(self, raw_password):
        return pbkdf2_sha256.verify(raw_password, self.password)

    @classmethod
    @duplicate_handle(errors.UserAlreadyExists)
    def new_user(cls, email, password, role, name=None):
        user = cls.get_by_email(email)
        if user:
            if user.deleted is None:
                raise errors.UserAlreadyExists()
            existed = True
        else:
            user = cls()
            existed = False

        user.email = email
        user.password = cls.password_hashing(password) if password else ""
        user.role = role
        user.name = name
        user.deleted = None
        user.created = utcnow().datetime

        if not existed:
            db.session.add(user)
        return user

    @classmethod
    def get_by_email(cls, email, include_deleted=False):
        query = cls.query.filter_by(email=email)
        if not include_deleted:
            query.filter_by(deleted=None)
        return query.first()

    @classmethod
    def login(cls, email, password):
        user = User.get_by_email(email)

        if user is None:
            logbook.info("User {} is not found", email)
            raise errors.UserUnauthorized()
        if user.deleted:
            logbook.info("User {} is deleted at {}", email, user.deleted)
            raise errors.UserUnauthorized()

        if not user.check_password(password):
            logbook.info("Password mismatch for user {}", email)
            raise errors.UserUnauthorized()

        token = UserToken.create(user)

        return token, user

    def update(self, new_parameters):
        password = new_parameters.get("password")
        if password:
            new_parameters["password"] = self.password_hashing(password)
        return super().update(new_parameters)

    def mark_removed(self):
        res = super().mark_removed()
        UserToken.remove_by(self.user_id)
        return res

    def password_reset(self, password):
        self.password = self.password_hashing(password)
