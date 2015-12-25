# -*- coding: utf-8 -*-
from jinja2 import contextfunction, Environment, FileSystemLoader, StrictUndefined
from jinja2.ext import Extension
from z3c.rml.rml2pdf import parseString
from report import Render
from report.render import float_pretty_format, sort_multi, sort_services
from babel.dates import format_datetime, format_date, format_timedelta
from utils.i18n import _, localize_money


class Translation(Extension):
    def __init__(self, environment):
        Extension.__init__(self, environment)
        environment.globals['tr'] = self.translate
        self._prepared_translations = {}

    def get_prepared_translation(self, context):
        language = context.parent["language"]
        translation_key = "{}-{}".format(context.name, language)
        prepared_translation = self._prepared_translations.get(translation_key)
        if prepared_translation is not None:
            return prepared_translation

        translation = context.vars.get("translation")
        languages = translation[0]
        try:
            language_index = languages.index(language)
        except ValueError:
            language_index = 0

        self._prepared_translations[translation_key] = prepared_translation = {}
        for t in translation[1:]:
            prepared_translation[t[0]] = t[language_index]
        return prepared_translation

    @contextfunction
    def translate(self, context, text, *args):
        translation = self.get_prepared_translation(context)

        text = (translation.get(text) or translation.get(text.lower()) or
                translation.get(text.upper()) or text)
        if args:
            text = text.format(*args)

        return text


class PdfRender(Render):
    output_format = "pdf"


    def __init__(self, template_dir=None):
        super(PdfRender, self).__init__(template_dir)
        self.environment = Environment(loader=FileSystemLoader(self.template_dir),
                                       auto_reload=False,
                                       autoescape=True,
                                       extensions=[Translation],
                                       undefined=StrictUndefined)
        self.environment.filters["pretty_float"] = float_pretty_format
        self.environment.filters["sort_multi"] = sort_multi
        self.environment.filters["sort_services"] = sort_services
        self.environment.filters["datetime"] = format_datetime
        self.environment.filters["date"] = format_date
        self.environment.filters["timedelta"] = format_timedelta
        self.environment.filters["money"] = localize_money

    def _render(self, aggregated, configuration, locale, language, **kwargs):
        template_name = configuration["template"]
        template = self.environment.get_template(template_name)
        rendered = template.render(aggregated=aggregated,
                                   locale=locale, language=language, font_dir=self.template_dir,
                                   **kwargs)
        return parseString(rendered).getvalue()
