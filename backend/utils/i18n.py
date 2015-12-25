import conf
import sys
import os
from decimal import Decimal
from collections import defaultdict
from gettext import translation
from babel import Locale, UnknownLocaleError, localedata
from babel.numbers import parse_decimal, format_currency, format_decimal
from bottle import request
from functools import lru_cache
from os.path import join
from lib import root_directory


LOCALE_DIR = join(root_directory(), 'backend', 'locale')
DEFAULT_LANGUAGE = conf.ui.default_language
SUPPORTED_LOCALES = frozenset(localedata.locale_identifiers())
APPLICATION_NAME = "boss"


def _(message):
    return message


def acceptable_languages():
    languages = languages_set_from_headers()
    languages.intersection_update(available_languages())
    languages -= {DEFAULT_LANGUAGE}

    return list(languages) if languages else [DEFAULT_LANGUAGE]


def languages_set_from_headers():
    try:
        codes = request.headers.get('Accept-Language', DEFAULT_LANGUAGE).split(',')
    except RuntimeError:
        # RuntimeError can happen if it's called not in request context
        return set()
    languages = set()
    for code in codes:
        language = language_from_locale(code, "")
        if language:
            languages.add(language)
    return languages


def translate(message, language=None):
    if language is None:
        language = preferred_language()

    gettext = translations().get(language)
    if not gettext:
        raise ValueError('Cannot find translation for {} language'.format(language))

    return gettext.gettext(message)


@lru_cache()
def language_from_locale(code, default=DEFAULT_LANGUAGE):
    if not code:
        return default
    try:
        return Locale.parse(code.replace(u'-', u'_').strip()).language
    except (ValueError, UnknownLocaleError, TypeError):
        return default


def localize_money(money, currency=None, language=None):
    if language is None:
        language = preferred_language()

    if not isinstance(money, Decimal):
        money = parse_decimal(money)

    if currency:
        return format_currency(money, currency, locale=language)
    else:
        return format_decimal(money, locale=language, format="#,##0.00")


def preferred_language():
    """ It just returns first language from acceptable
    """
    return acceptable_languages()[0]


@lru_cache()
def all_languages():
    locales = all_locales()
    return {code: names for code, names in locales.items() if '_' not in code}


@lru_cache()
def all_locales():
    result = defaultdict(dict)

    for code in SUPPORTED_LOCALES:
        locale = Locale.parse(code)
        for language in available_languages():
            try:
                result[code][language] = locale.get_display_name(locale=language)
            except Exception:
                pass

    return result


@lru_cache()
def available_languages():
    return frozenset(name for name in os.listdir(LOCALE_DIR)
                     if len(name) == 2 and os.path.isdir(join(LOCALE_DIR, name)))


@lru_cache()
def translations():
    return {lang: translation(APPLICATION_NAME, LOCALE_DIR, (lang,)) for lang in available_languages()}


def extract_translations():
    from babel.messages.frontend import CommandLineInterface
    os.chdir(root_directory())

    pot_file = join(LOCALE_DIR, "%s.pot" % APPLICATION_NAME)
    CommandLineInterface().run([__file__, "extract", "-w", "225",
                                "-o", pot_file, "--mapping", join(os.path.dirname(__file__), "mapping.cfg"),
                                "backend"])

    for language in available_languages():
        po_file = join(LOCALE_DIR, language, "LC_MESSAGES", "%s.po" % APPLICATION_NAME)
        args = ["-D", APPLICATION_NAME, "-i", pot_file, "-d", LOCALE_DIR, "--no-wrap", "-l", language]
        command = "update" if os.path.exists(po_file) else "init"
        if os.path.exists(po_file):
            args.append("--no-fuzzy-matching")

        CommandLineInterface().run([__file__, command] + args)
    return True


def compile_translations():
    from babel.messages.frontend import CommandLineInterface

    os.chdir(root_directory())
    res = True
    for language in available_languages():
        po_file = join(LOCALE_DIR, language, "LC_MESSAGES", "%s.po" % APPLICATION_NAME)
        if language != "en":
            msgid = None
            with open(po_file, "br") as f:
                for line in f:
                    line = line.decode("utf-8").rstrip()
                    if msgid is None:
                        if line.startswith("msgid "):
                            msgid = line[len("msgid "):]
                            if msgid == '""':
                                msgid = None
                    else:
                        if line.startswith("msgstr "):
                            msgstr = line[len("msgstr "):]
                            if msgstr == '""':
                                res = False
                                print("Found untranslated message for %s: %s" % (language, msgid))
                            msgid = None

        CommandLineInterface().run([__file__, "compile", "-D", APPLICATION_NAME,
                                    "-i", po_file, "-d", LOCALE_DIR,
                                    "-l", language, "--statistics"])
    return res


def main():
    """
    Prepare translations files

    Usage:
        i18n extract [options]
        i18n compile [options]

    Options:
      -h --help                 Show this screen.
    """
    import docopt
    opt = docopt.docopt(main.__doc__)
    if opt["extract"]:
        res = extract_translations()
    elif opt["compile"]:
        res = compile_translations()
    else:
        raise Exception("Unknown command")
    if not res:
        sys.exit(1)


if __name__ == '__main__':
    main()
