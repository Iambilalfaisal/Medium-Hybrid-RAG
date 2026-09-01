import html
import re
import unicodedata

from app.config import settings

_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_MULTI_SPACE_RE = re.compile(r"[ \t]+")
_MULTI_BLANK_LINE_RE = re.compile(r"\n{3,}")


def clean_text(raw: str | None) -> str | None:
    """Pure function: no DB, no network, no file I/O. Sanitizes trafilatura output
    (HTML entities, control chars, inconsistent Unicode forms, ragged whitespace) and
    rejects anything too short to be a real article body — treated by callers as a
    failed scrape, not silently embedded as low-signal noise."""
    if not raw:
        return None

    text = html.unescape(raw)
    text = unicodedata.normalize("NFKC", text)
    text = _CONTROL_CHARS_RE.sub("", text)
    text = _MULTI_SPACE_RE.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = _MULTI_BLANK_LINE_RE.sub("\n\n", text)
    text = text.strip()

    if len(text) < settings.MIN_TEXT_LENGTH:
        return None

    return text
