"""Process coverage data files into reports.
Enable coverage in current process.

Usage:
    coverage_report.py (report|html) [options] <FILE>
    coverage_report.py teamcity [--rcfile=FILE] <FILE>

Options:
    --morfs ...   Modules names or paths. Each module in morfs is listed, with counts of statements,
                  executed statements, missing statements, and a list of lines missed.
    --omit ...    Modules matching omit will not be included in the report.
    --include ... A list of filename patterns. Modules whose filenames match those patterns
                  will be included in the report.

    --show_missing BOOL  Report only [default=True]
    --file FILE          Report only. Write a summary report to file. Otherwise it will be printed to stdout.

    --directory FILE  Html only. Directory where html report is written.
    --extra_css FILE  Html only. A path to a file of other CSS to apply on the page.
                      It will be copied into the HTML directory.
    --rcfile FILE Coverage config file
"""
from coverage.results import Numbers

_coverages = dict()


def coverage_on_exit():
    for cov in _coverages.values():
        cov.stop()
        cov.save()


def coverage_on_start(config: dict, register_exit: bool=True):
    import atexit
    import os
    import coverage

    global _coverages

    _coverages[os.getpid()] = coverage.coverage(**config)
    if register_exit:
        atexit.register(coverage_on_exit)
    _coverages[os.getpid()].start()


def html(data_file, morfs=None, directory=None, ignore_errors=None, omit=None, include=None, extra_css=None,
         title=None) -> float:
    """
    Generate an HTML report.

    :param data_file: Coverage data file.
    :param morfs: Module name or path. Each module in morfs is listed, with counts of statements, executed statements,
                  missing statements, and a list of lines missed.
    :param directory: Directory where html report is written.
    :param ignore_errors: Unknown
    :param omit: Modules matching omit will not be included in the report.
    :param include: A list of filename patterns. Modules whose filenames match those patterns
                    will be included in the report.
    :param extra_css: A path to a file of other CSS to apply on the page. It will be copied into the HTML directory.
    :param title: A text string (not HTML) to use as the title of the HTML report.
    :return: A float, the total percentage covered.
    """
    import coverage
    c = coverage.coverage(data_file=data_file)
    c.load()
    c.combine()
    return c.html_report(morfs=morfs, directory=directory, ignore_errors=ignore_errors, omit=omit, include=include,
                         extra_css=extra_css, title=title)


def report(data_file, morfs=None, show_missing=None, ignore_errors=None, file=None, omit=None, include=None) -> float:
    """
    Generate a summary report.

    :param data_file: Coverage data file
    :param morfs: Module name or path. Each module in morfs is listed, with counts of statements, executed
                  statements, missing statements, and a list of lines missed.
    :param show_missing: Unknown
    :param ignore_errors: Unknown
    :param file: Write a summary report to file. Otherwize it will be printed to stdout.
    :param omit: Modules matching omit will not be included in the report.
    :param include: A list of filename patterns. Modules whose filenames match those patterns
                    will be included in the report.
    :return: A float, the total percentage covered.
    """
    import coverage
    c = coverage.coverage(data_file=data_file)
    c.load()
    if file:
        file = open(str(file), 'w')
    c.combine()
    return c.report(morfs=morfs, show_missing=show_missing, ignore_errors=ignore_errors,
                    file=file, omit=omit,
                    include=include)


def teamcity_report(data_file, config_file=None):
    """
    Generate teamcity coverage report.

    :param data_file: Coverage data file
    :param config_file: Config file for coverage
    """
    import coverage
    from teamcity import messages

    service_messages = messages.TeamcityServiceMessages()
    cov = coverage.Coverage(data_file, config_file=config_file)
    cov.load()

    total_nums = Numbers()
    for path in cov.data.measured_files():
        if path.endswith("py"):
            analysis = cov._analyze(path)
            total_nums += analysis.numbers

    service_messages.buildStatisticLinesCovered(total_nums.n_executed)
    service_messages.buildStatisticTotalLines(total_nums.n_statements)


if __name__ == '__main__':
    import docopt

    args = docopt.docopt(__doc__)
    run_report = args.pop('report')
    run_html = args.pop('html')
    run_teamcity = args.pop('teamcity')

    run_args = {'data_file': args.pop('<FILE>')}
    for argname, value in args.items():
        if not value is None:
            run_args[argname[2:]] = value

    if run_report:
        report(**run_args)
    elif run_html:
        html(**run_args)
    elif run_teamcity:
        teamcity_report(data_file=run_args['data_file'], config_file=run_args['rcfile'])
