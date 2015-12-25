"""
Perform databases migration

Usage:
    migrate revision [options]
    migrate merge <revisions>... [options]
    migrate upgrade [<revision>] [options]
    migrate downgrade [<revision>] [options]
    migrate show [<revision>] [options]
    migrate history [options]
    migrate heads [options]
    migrate branches [options]
    migrate current [options]
    migrate stamp [options]



Options:
  -h --help                 Show this screen.
  --rev-id=REV_ID           Specify a hardcoded revision id instead of generating one
  --branch-label=BRANCH     Specify a branch label to apply to the new revision
  --splice                  Allow a non-head revision as the "head" to splice onto
  --head=HEAD               Specify head revision or <branchname>@head to base new revision on
  --sql                     Don't emit SQL to database - dump to standard output instead
  --autogenerate            Populate revision script with candidate migration operations, based on comparison of database to model
  -m --message              Message for the revision
  --rev-range=RAGE          Specify a revision range; format is [start]:[end]
  -v --verbose             Use more verbose output
  --resolve-dependencies    Treat dependency versions as down revisions
"""
import os
import docopt
from alembic.config import Config
from alembic import command


def _get_config(directory=None):
    directory = directory or os.path.dirname(__file__)
    config = Config(os.path.join(directory, 'alembic.ini'))
    config.set_main_option('script_location', directory)
    return config


def revision(opt, config):
    command.revision(config, opt["--message"] or None, autogenerate=opt["--autogenerate"], sql=opt["--sql"],
                     head=opt["--head"], splice=opt["--splice"], branch_label=opt["--branch-label"],
                     rev_id=opt["--rev-id"])


def merge(opt, config):
    command.merge(config, opt["<revisions>"], message=opt["--message"],
                  branch_label=opt["--branch-label"], rev_id=opt["--rev-id"])


def upgrade(opt, config):
    command.upgrade(config, opt["<revisions>"] or "head", sql=opt["--sql"])


def downgrade(opt, config):
    command.downgrade(config, opt["<revisions>"] or "-1", sql=opt["--sql"])


def show(opt, config):
    command.show(config, opt["<revisions>"] or "head")


def history(opt, config):
    command.history(config, opt["--rev-range"], verbose=opt["--verbose"])


def heads(opt, config):
    command.heads(config, verbose=opt["--verbose"], resolve_dependencies=opt["--resolve-dependencies"])


def branches(opt, config):
    command.branches(config, verbose=opt["--verbose"])


def current(opt, config):
    command.current(config, verbose=opt["--verbose"])


def stamp(opt, config):
    command.stamp(config, opt["<revision>"] or "head", sql=opt["--sql"])


def main():
    opt = docopt.docopt(__doc__)
    config = _get_config()
    if opt["revision"]:
        revision(opt, config)
    elif opt["merge"]:
        merge(opt, config)
    elif opt["upgrade"]:
        upgrade(opt, config)
    elif opt["downgrade"]:
        downgrade(opt, config)
    elif opt["show"]:
        show(opt, config)
    elif opt["history"]:
        history(opt, config)
    elif opt["heads"]:
        heads(opt, config)
    elif opt["branches"]:
        branches(opt, config)
    elif opt["current"]:
        current(opt, config)
    elif opt["stamp"]:
        stamp(opt, config)
    else:
        raise Exception("Unknown command")


if __name__ == '__main__':
    main()
