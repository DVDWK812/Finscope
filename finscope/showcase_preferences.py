"""Session-scoped display preferences. No I/O, translation service or model."""
from contextlib import contextmanager
from contextvars import ContextVar
from html import escape
from html.parser import HTMLParser

from .showcase_zh import ZH

LANGUAGE = ContextVar("showcase_language", default="en")
APPEARANCE = ContextVar("showcase_appearance", default="dark")


@contextmanager
def preferences(language="en", appearance="dark"):
    """Keep concurrent Streamlit sessions independent, including after errors."""
    language_token = LANGUAGE.set(language if language in ("en", "zh-CN") else "en")
    appearance_token = APPEARANCE.set(appearance if appearance in ("dark", "light") else "dark")
    try:
        yield
    finally:
        LANGUAGE.reset(language_token)
        APPEARANCE.reset(appearance_token)


def t(message, **values):
    translated = ZH.get(message, message) if LANGUAGE.get() == "zh-CN" else message
    return translated.format(**values) if values else translated


def display_formatter():
    """Bind the locale for callbacks serialized after this render finishes."""
    chinese = LANGUAGE.get() == "zh-CN"
    return lambda message: ZH.get(message, message) if chinese else message


class _MarkupTranslator(HTMLParser):
    """Translate authored text/accessible labels, never CSS, scripts or IDs."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.output = []
        self.verbatim = 0

    def handle_starttag(self, tag, attrs):
        self.verbatim += tag in ("style", "script")
        attributes = ''.join(' ' + key + ('' if value is None else '="' + escape(
            t(value) if key in ("aria-label", "title") else value, quote=True) + '"')
            for key, value in attrs)
        self.output.append('<' + tag + attributes + '>')

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.output[-1] = self.output[-1][:-1] + ' />'

    def handle_endtag(self, tag):
        self.verbatim -= tag in ("style", "script")
        self.output.append('</' + tag + '>')

    def handle_data(self, data):
        if self.verbatim:
            self.output.append(data)
        else:
            # Preserve spacing around inline elements (for example badge dots).
            stripped = data.strip()
            self.output.append(escape(data.replace(stripped, t(stripped), 1) if stripped else data))


def localize_html(markup):
    if LANGUAGE.get() == "en":
        return markup
    translator = _MarkupTranslator()
    translator.feed(markup)
    return ''.join(translator.output)


def translated_markup(function):
    def render(*args, **kwargs):
        return localize_html(function(*args, **kwargs))
    return render
