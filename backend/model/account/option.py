import errors
import logbook
from model import db, duplicate_handle
from sqlalchemy import Column
from sqlalchemy.orm.exc import NoResultFound


class Option(db.Model):
    key = Column(db.String(32), primary_key=True, nullable=False)
    value = Column(db.String(32))

    @classmethod
    @duplicate_handle(errors.OptionAlreadyExists)
    def create(cls, key, value):
        option = cls()

        option.key = key
        option.value = value

        db.session.add(option)
        db.session.commit()

    @classmethod
    def set(cls, key, value):
        option = cls.query.get(key)
        if option:
            option.value = value
            db.session.commit()
        else:
            option = cls.create(key, value)

        return option

    @classmethod
    def get(cls, key):
        try:
            return cls.query.filter(cls.key == key).one().value
        except NoResultFound:
            logbook.info('Key {} not found', key)