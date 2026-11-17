"""Turning plain text into safe LaTeX."""

from __future__ import annotations

import re

_SPECIAL = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
    "<": r"\textless{}",
    ">": r"\textgreater{}",
}
_SPECIAL_RE = re.compile("|".join(re.escape(c) for c in _SPECIAL))
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"(?<![\w*])_(.+?)_(?![\w*])")


def escape(value: object) -> str:
    """Escape every LaTeX special character. Use for any text that comes from YAML."""
    if value is None:
        return ""
    return _SPECIAL_RE.sub(lambda m: _SPECIAL[m.group(0)], str(value))


def inline(value: object) -> str:
    """Escape, then honour a tiny markdown subset: **bold** and _italic_.

    The markers are found on the raw text first, so a literal `_` inside a word
    (snake_case) is never mistaken for italics.
    """
    if value is None:
        return ""
    raw = str(value)
    out: list[str] = []
    pos = 0
    pattern = re.compile(f"{_BOLD_RE.pattern}|{_ITALIC_RE.pattern}")
    for m in pattern.finditer(raw):
        out.append(escape(raw[pos:m.start()]))
        if m.group(1) is not None:
            out.append(r"\textbf{" + escape(m.group(1)) + "}")
        else:
            out.append(r"\textit{" + escape(m.group(2)) + "}")
        pos = m.end()
    out.append(escape(raw[pos:]))
    return "".join(out)


def url(value: str) -> str:
    """Escape a URL for use as the first argument of \\href (hyperref keeps most chars)."""
    return value.replace("\\", "/").replace("%", r"\%").replace("#", r"\#")


def display_url(value: str) -> str:
    """Shorter, human-readable form of a URL for printing."""
    shown = re.sub(r"^https?://(www\.)?", "", value).rstrip("/")
    return escape(shown)
