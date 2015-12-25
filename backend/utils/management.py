"""
Management of BOSS infrastructure

Usage: bossmngr checkconfig

Options:
    --prefix=<prefix> Prefix to delete
    --field=<field> Field to search in

"""
import sys
SUCCESS = 0
FAILED = 1


def main():
    import docopt
    from utils.check_config import print_check_config

    opt = docopt.docopt(__doc__)
    if opt['checkconfig']:
        status = print_check_config()
        return SUCCESS if status else FAILED


if __name__ == '__main__':
    sys.exit(main())
