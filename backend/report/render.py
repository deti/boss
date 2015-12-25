import operator
import conf
import logbook
from tempfile import mkdtemp
from utils.i18n import language_from_locale


def float_pretty_format(f, precession=2, max_precession=10):
    if not isinstance(f, float):
        return f
    sign = "-" if f < 0 else ""

    f = abs(f)
    if f < 1:
        fd = f
        while fd < 0.1 and precession < max_precession:
            precession += 1
            fd *= 10

    result = "%s%.{0}f".format(precession) % (sign, f)
    return result.rstrip("0")


def sort_multi(l, *operators):
    try:
        return sorted(l, key=operator.itemgetter(*operators))
    except TypeError:
        return sorted(l, key=operator.attrgetter(*operators))


def sort_services(services):
    """ Jinja filter. Sorts `services` by category and HW params or name
    """
    def key(service):
        category = service["category"]
        rt_key = _rt_service_sort_key(service["service_id"])
        if rt_key is not None:
            return category, rt_key
        return category, service["name"]

    return sorted(services, key=key)


class Render(object):
    output_format = None
    formats = {}

    def __init__(self, template_dir=None):
        self.template_dir = template_dir or conf.report.template_dir

    @classmethod
    def register_all_formats(cls):
        from report.json_render import JsonRender
        from report.csv_render import CSVRender, TSVRender
        from report.pdf_render import PdfRender
        PdfRender.register_format()
        # XlsxRender.register_format()
        JsonRender.register_format()
        CSVRender.register_format()
        TSVRender.register_format()

    @classmethod
    def register_format(cls):
        cls.formats[cls.output_format] = cls()

    @classmethod
    def get_render(cls, format_):
        if not cls.formats:
            cls.register_all_formats()
        return cls.formats[format_]

    def get_temporary_dir(self):
        return mkdtemp(prefix="BOSS", suffix=self.output_format)

    def config_format(self):
        return self.output_format

    def get_configuration(self, report_type, locale):
        language = language_from_locale(locale)
        LOCALIZED = "_localized"
        LEN_LOCALIZED = len(LOCALIZED)
        configuration = conf.report.configuration[report_type][self.config_format()]
        if not configuration:
            configuration = {}
        result = {key: value for key, value in configuration.items()if not key.endswith(LOCALIZED)}
        for key, value in configuration.items():
            if key.endswith(LOCALIZED):
                k = key[:-LEN_LOCALIZED]
                localized_value = value.get(locale)
                if localized_value:
                    result[k] = localized_value
                    continue
                localized_value = value.get(language)
                if localized_value:
                    result[k] = localized_value

        return result

    def _render(self, aggregated, configuration, locale, language, **kwargs):
        raise NotImplementedError()

    def render(self, aggregated, report_type, locale, **kwargs):
        logbook.info("Rendering {} and locale {}", report_type, locale)
        configuration = self.get_configuration(report_type, locale)
        return self._render(aggregated, configuration, locale=locale, language=language_from_locale(locale), **kwargs)
