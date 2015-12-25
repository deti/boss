import json
from report import Render
from utils import DateTimeJSONEncoder


class JsonRender(Render):
    output_format = "json"

    def __init__(self, template_dir=None):
        super().__init__(template_dir)

    def _render(self, aggregated, configuration, locale, language, **kwargs):
        return json.dumps(aggregated, cls=DateTimeJSONEncoder).encode("utf-8")
