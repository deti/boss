"""
Cleans database from test entities

Usage: db_clean [TABLES ...] [--prefix=<prefix>] [--field=<field>]

Options:
    --prefix=<prefix> Prefix to delete
    --field=<field> Field to search in

"""
import conf
import logbook

from collections import OrderedDict
from model import db, Customer, User, Service, ServiceLocalization, ServiceDescription, Tariff, News, Tenant, Deferred
from utils import setup_backend_logbook


def delete_by_prefix(table, prefix, field):
    if field is not None:
        columns = {field: getattr(table, field)}
    else:
        columns = {c.name: c for c in table.__table__.columns if c.name != 'customer_mode'}

    for name, value in columns.items():
        if hasattr(table, 'delete_by_prefix'):
            table.delete_by_prefix(prefix=prefix, field=name)
        else:
            table.query.filter(value.like(prefix + "%")).delete(False)


def main():
    with setup_backend_logbook("stderr"):
        import docopt
        opt = docopt.docopt(__doc__)
        prefix = opt['--prefix'] or conf.devel.test_prefix
        field = opt['--field']

        deletable_tables = OrderedDict([
            ('customer', Customer), ('tariff', Tariff), ('news', News),
            ('service_localization', ServiceLocalization), ('service_description', ServiceDescription),
            ('service', Service),
            ('fitter_tenants', Tenant),
            ('deferred', Deferred), ('user', User)])

        tables = opt["TABLES"] or deletable_tables.keys()

        for table in tables:
            logbook.info("Force removing objects from {} with prefix {}", table, prefix)
            if table is not None:
                delete_by_prefix(deletable_tables[table], prefix, field)
            db.session.commit()

        db.session.commit()

if __name__ == '__main__':
    main()
