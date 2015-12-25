import conf
from alembic import context
from sqlalchemy import engine_from_config, pool
from logging.config import fileConfig
import logging
from model import db
from sqlalchemy.sql.sqltypes import Boolean
from sqlalchemy.dialects.mysql.base import TINYINT

USE_TWOPHASE = False

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)
logger = logging.getLogger('alembic.env')


config.set_main_option('sqlalchemy.url', conf.database.uri)

db_uri = {"account": conf.database.uri}
db_uri.update(conf.database.binds)


class FakeMetadata(object):
    def __init__(self, bind):
        tables = db.get_tables_for_bind(bind)
        self.tables = {name: t for name, t in db.metadata.tables.items() if t in tables}
        self.sorted_tables = [t for t in db.metadata.sorted_tables if t in tables]

target_metadata = {"fitter": FakeMetadata("fitter"),
                   "account": FakeMetadata(None)}

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def compare_type(context, inspected_column,
            metadata_column, inspected_type, metadata_type):
    # return True if the types are different,
    # False if not, or None to allow the default implementation
    # to compare these types
    if isinstance(metadata_type, Boolean) and isinstance(inspected_type, TINYINT):
        return False
    return None


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # for the --sql use case, run migrations for each URL into
    # individual files.

    engines = {}
    for name in db_uri:
        engines[name] = rec = {}
        rec['url'] = db_uri[name]

    for name, rec in engines.items():
        logger.info("Migrating database %s" % name)
        file_ = "%s.sql" % name
        logger.info("Writing output to %s" % file_)
        with open(file_, 'w') as buffer:
            context.configure(url=rec['url'], output_buffer=buffer,
                              target_metadata=target_metadata.get(name),
                              compare_type=compare_type)
            with context.begin_transaction():
                context.run_migrations(engine_name=name)


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    # for the direct-to-DB use case, start a transaction on all
    # engines, then run all migrations, then commit all transactions.

    engines = {}
    for name in db_uri:
        engines[name] = rec = {}
        rec['url'] = db_uri[name]
        rec['engine'] = engine_from_config(
            {"sqlalchemy.url": db_uri[name]},
            prefix='sqlalchemy.',
            poolclass=pool.NullPool)

    for name, rec in engines.items():
        engine = rec['engine']
        rec['connection'] = conn = engine.connect()

        if USE_TWOPHASE:
            rec['transaction'] = conn.begin_twophase()
        else:
            rec['transaction'] = conn.begin()

    try:
        for name, rec in engines.items():
            logger.info("Migrating database %s" % name)
            context.configure(
                connection=rec['connection'],
                upgrade_token="%s_upgrades" % name,
                downgrade_token="%s_downgrades" % name,
                target_metadata=target_metadata.get(name),
                compare_type=compare_type
            )
            context.run_migrations(engine_name=name)

        if USE_TWOPHASE:
            for rec in engines.values():
                rec['transaction'].prepare()

        for rec in engines.values():
            rec['transaction'].commit()
    except:
        for rec in engines.values():
            rec['transaction'].rollback()
        raise
    finally:
        for rec in engines.values():
            rec['connection'].close()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
