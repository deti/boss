"""
Manage user access to mysql

Usage:
    db_user create [options]
    db_user create_test [options]
    db_user drop [options]
    db_user drop_test [options]
    db_user dropdb [options]
    db_user dropdb_test [options]

Options:
  -h --help                 Show this screen.
  -u --user=USER            Username with ROOT privileges
  -p --password=PASSWORD    Password
  -h --hostname=HOSTNAME    Hostname for grant access. By default it is % from create method and
                            localhost for create_test
  --splice                  Allow a non-head revision as the "head" to splice onto
  --head=HEAD               Specify head revision or <branchname>@head to base new revision on
  --sql                     Don't emit SQL to database - dump to standard output instead
  --autogenerate            Populate revision script with candidate migration operations, based on
                            comparison of database to model
  -m --message              Message for the revision
  --rev-range=RAGE          Specify a revision range; format is [start]:[end]
  -v --verbose              Use more verbose output
  --resolve-dependencies    Treat dependency versions as down revisions
"""
import conf
import docopt
import pymysql


# noinspection PyPep8Naming
from sqlalchemy.engine.url import make_url


class cached_property(object):
    """ A property that is only computed once per instance and then replaces
        itself with an ordinary attribute. Deleting the attribute resets the
        property.
    """

    def __init__(self, func):
        self.func = func

    # noinspection PyUnusedLocal
    def __get__(self, obj, cls):
        if obj is None:
            return self
        value = obj.__dict__[self.func.__name__] = self.func(obj)
        return value


class DBUserManager(object):
    def __init__(self):
        self.opt = docopt.docopt(__doc__)
        self.url = make_url(conf.database.uri)
        self.url_test = make_url(conf.database.test.uri)
        self.default_port = 3306

    @cached_property
    def mysql(self):
        connection = pymysql.connect(host=self.url.host,
                                     user=self.opt["--user"],
                                     passwd=self.opt["--password"],
                                     port=self.url.port or self.default_port)
        return connection

    def grant(self, user, password, dbname='*', table_name='*', hostname="localhost"):
        self.execute("GRANT ALL ON %s.%s TO '%s'@'%s' IDENTIFIED BY '%s';" % (dbname, table_name,
                                                                              user, hostname, password))

    def execute(self, sql, params=None):
        with self.mysql.cursor() as cursor:
            if params:
                print("%s with parameters %s" % (sql, params))
            else:
                print(sql)
            cursor.execute(sql, params)

    def create_db(self, dbname):
        self.execute("CREATE DATABASE IF NOT EXISTS %s CHARACTER SET utf8 COLLATE utf8_general_ci;" % dbname)

    def _create(self, url, binds):
        created_uri = set()
        self.create_db(url.database)
        self.grant(url.username, url.password, url.database, hostname=self.opt["--hostname"] or "%")
        created_uri.add(url.__to_string__(hide_password=False))
        for name, uri in binds.items():
            if uri not in created_uri:
                u = make_url(uri)
                self.create_db(u.database)
                created_uri.add(uri)
                self.grant(u.username, u.password, u.database, hostname=self.opt["--hostname"] or "%")

    def create(self):
        """ Create user and databases. Also privileges is granted for this user and database"""
        self._create(self.url, conf.database.binds)

    def create_test(self):
        """ Create user and databases for unit tests. Also ALL privileges is granted for this user for this user"""
        self._create(self.url_test, conf.database.test.binds)

    def drop_user(self, user):
        self.execute("DROP USER '%s';" % user)

    def drop(self):
        self.drop_user(self.url.username)

    def drop_test(self):
        self.drop_user(self.url_test.username)

    def drop_db(self, dbname):
        self.execute("DROP DATABASE IF EXISTS %s ;" % dbname)

    def drop_dbs(self, url, binds):
        deleted_uri = set()
        self.drop_db(url.database)
        deleted_uri.add(url.__to_string__(hide_password=False))
        for uri in binds.values():
            if uri not in deleted_uri:
                u = make_url(uri)
                self.drop_db(u.database)
                deleted_uri.add(uri)

    def run(self):
        if self.opt["create"]:
            return self.create()
        elif self.opt["create_test"]:
            return self.create_test()
        elif self.opt["drop"]:
            return self.drop()
        elif self.opt["drop_test"]:
            return self.drop_test()
        elif self.opt["dropdb"]:
            return self.drop_dbs(self.url, conf.database.binds)
        elif self.opt["dropdb_test"]:
            return self.drop_dbs(self.url_test, conf.database.test.binds)
        else:
            raise Exception("Unknown command")


def main():
    manager = DBUserManager()
    manager.run()

if __name__ == '__main__':
    main()
