import os
import logbook
from functools import lru_cache


@lru_cache()
def root_directory(application_path=None):
    root_path = application_path or os.path.dirname(__file__)
    while root_path and "bin" not in os.listdir(root_path):
        root_path = os.path.dirname(root_path)
    return root_path


@lru_cache()
def config_stage_directory():
    root_path = root_directory()
    return os.path.join(root_path, "configs", "stage")


def exception_safe(fn):
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception:
            logbook.exception("{} raise exception", fn.__name__)

    return wrapper


@lru_cache()
def version(component="backend"):
    import yaml
    f = open(os.path.join(root_directory(), "version"), "rb")
    version_config = yaml.load(f)["version"]
    base = str(version_config["base"])
    return ".".join((base, str(version_config[component])))


@lru_cache()
def build_id():
    import yaml
    f = open(os.path.join(root_directory(), "build"), "rb")
    return yaml.load(f)["version"]

