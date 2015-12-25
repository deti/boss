import pep8

from teamcity.messages import TeamcityServiceMessages
from teamcity import __version__, is_running_under_teamcity


name = 'teamcity_stats'
version = __version__
enable_teamcity = is_running_under_teamcity()


def add_options(parser):
    parser.add_option('--teamcity_stats', default=False,
                      action='callback', callback=set_option_callback,
                      help="Enable teamcity stats messages")


def set_option_callback(option, opt, value, parser):
    global enable_teamcity
    enable_teamcity = True


def parse_options(options):
    if not enable_teamcity:
        return

    options.reporter = TeamcityStatisticsReport
    options.report = TeamcityStatisticsReport(options)
    options.jobs = None  # needs to be disabled, flake8 overrides the report if enabled


class TeamcityStatisticsReport(pep8.StandardReport):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.teamcity_messages = TeamcityServiceMessages()

    def report_statistics(self, error_key, value):
        self.teamcity_messages.message('buildStatisticValue', key='PEP8-'+error_key, value=str(value))

    def print_statistics(self, prefix=''):
        super().print_statistics(prefix)
        for error_key in sorted(self.messages):
            self.report_statistics(error_key, self.counters[error_key])
        self.report_statistics('TOTAL', self.get_count())
        self.report_statistics('TOTAL-ERRORS', self.get_count('E'))
        self.report_statistics('TOTAL-WARNINGS', self.get_count('W'))
