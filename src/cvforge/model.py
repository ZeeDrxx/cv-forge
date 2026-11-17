"""Load, validate and resolve a CV source file.

A source file holds every fact once. A *variant* (general, internship, masters…)
picks which items appear and in what order; a *language* picks which text is used.
Resolving (source, variant, language) gives a plain dict that the template renders.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

LANGUAGES = ("en", "fr")
SECTION_KINDS = ("text", "entries", "skills", "languages")

DEFAULT_HEADINGS = {
    "summary": {"en": "Profile", "fr": "Profil"},
    "experience": {"en": "Experience", "fr": "Expérience"},
    "projects": {"en": "Projects", "fr": "Projets"},
    "education": {"en": "Education", "fr": "Formation"},
    "skills": {"en": "Skills", "fr": "Compétences"},
    "languages": {"en": "Languages", "fr": "Langues"},
    "awards": {"en": "Awards", "fr": "Distinctions"},
    "certifications": {"en": "Certifications", "fr": "Certifications"},
}

MONTHS = {
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "fr": ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."],
}
PRESENT = {"en": "present", "fr": "présent"}

_DATE = re.compile(r"^(\d{4})(?:-(\d{2}))?$")


class CVError(ValueError):
    """A problem in the CV source file, with the path of the offending field."""

    def __init__(self, where: str, message: str):
        super().__init__(f"{where}: {message}")
        self.where = where


@dataclass(frozen=True)
class Target:
    variant: str
    lang: str

    @property
    def slug(self) -> str:
        return f"cv-{self.variant}-{self.lang}"


def load(path: str | Path) -> dict[str, Any]:
    """Read a YAML source file and validate it. Returns the raw (unresolved) data."""
    path = Path(path)
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise CVError(str(path), f"invalid YAML ({exc})") from exc
    validate(data)
    return data


# --------------------------------------------------------------------------- validation


def _is_localized(value: Any) -> bool:
    return isinstance(value, str) or (
        isinstance(value, dict) and value and set(value) <= set(LANGUAGES)
        and all(isinstance(v, str) for v in value.values())
    )


def _need(cond: bool, where: str, message: str) -> None:
    if not cond:
        raise CVError(where, message)


def _check_text(value: Any, where: str, required: bool = True) -> None:
    if value is None and not required:
        return
    _need(_is_localized(value), where, "expected a string or a {en: …, fr: …} mapping")


def _check_date(value: Any, where: str) -> None:
    if value in (None, "present"):
        return
    _need(isinstance(value, (str, int)) and bool(_DATE.match(str(value))), where,
          "expected YYYY, YYYY-MM or 'present'")


def validate(data: Any) -> None:
    _need(isinstance(data, dict), "<root>", "the file must be a mapping")
    for key in ("profile", "sections", "variants"):
        _need(key in data, "<root>", f"missing top-level key '{key}'")

    profile = data["profile"]
    _need(isinstance(profile, dict), "profile", "expected a mapping")
    _check_text(profile.get("name"), "profile.name")
    _check_text(profile.get("headline"), "profile.headline", required=False)
    _check_text(profile.get("location"), "profile.location", required=False)
    for key in ("email", "phone"):
        _need(profile.get(key) is None or isinstance(profile[key], str), f"profile.{key}", "expected a string")
    for i, link in enumerate(profile.get("links", []) or []):
        _need(isinstance(link, dict) and "url" in link, f"profile.links[{i}]", "expected {label, url}")

    sections = data["sections"]
    _need(isinstance(sections, dict) and sections, "sections", "expected a non-empty mapping")
    item_ids: set[str] = set()
    for sid, section in sections.items():
        where = f"sections.{sid}"
        _need(isinstance(section, dict), where, "expected a mapping")
        kind = section.get("kind")
        _need(kind in SECTION_KINDS, f"{where}.kind", f"expected one of {', '.join(SECTION_KINDS)}")
        _check_text(section.get("heading"), f"{where}.heading", required=sid not in DEFAULT_HEADINGS)
        items = section.get("items", [])
        _need(isinstance(items, list), f"{where}.items", "expected a list")
        for i, item in enumerate(items):
            iw = f"{where}.items[{i}]"
            _need(isinstance(item, dict), iw, "expected a mapping")
            if "id" in item:
                _need(item["id"] not in item_ids, f"{iw}.id", f"duplicate id '{item['id']}'")
                item_ids.add(item["id"])
            tags = item.get("tags")
            _need(tags is None or (isinstance(tags, list) and all(isinstance(t, str) for t in tags)),
                  f"{iw}.tags", "expected a list of variant names")
            if kind == "text":
                _check_text(item.get("text"), f"{iw}.text")
            elif kind == "entries":
                _check_text(item.get("title"), f"{iw}.title")
                for opt in ("org", "location", "note"):
                    _check_text(item.get(opt), f"{iw}.{opt}", required=False)
                _check_date(item.get("start"), f"{iw}.start")
                _check_date(item.get("end"), f"{iw}.end")
                for j, bullet in enumerate(item.get("bullets", []) or []):
                    _check_text(bullet, f"{iw}.bullets[{j}]")
            elif kind == "skills":
                _check_text(item.get("group"), f"{iw}.group")
                _need(isinstance(item.get("items"), list) and item["items"], f"{iw}.items",
                      "expected a non-empty list")
            elif kind == "languages":
                _check_text(item.get("name"), f"{iw}.name")
                _check_text(item.get("level"), f"{iw}.level")

    variants = data["variants"]
    _need(isinstance(variants, dict) and variants, "variants", "expected a non-empty mapping")
    for vid, variant in variants.items():
        where = f"variants.{vid}"
        _need(isinstance(variant, dict), where, "expected a mapping")
        order = variant.get("sections")
        _need(isinstance(order, list) and order, f"{where}.sections", "expected a list of section ids")
        for sid in order:
            _need(sid in sections, f"{where}.sections", f"unknown section '{sid}'")
        for sid, limit in (variant.get("limits") or {}).items():
            _need(sid in sections, f"{where}.limits", f"unknown section '{sid}'")
            _need(isinstance(limit, int) and limit > 0, f"{where}.limits.{sid}", "expected a positive integer")
        _check_text(variant.get("headline"), f"{where}.headline", required=False)
        langs = variant.get("languages", list(LANGUAGES))
        _need(isinstance(langs, list) and set(langs) <= set(LANGUAGES), f"{where}.languages",
              f"expected a subset of {list(LANGUAGES)}")


# --------------------------------------------------------------------------- resolution


def text(value: Any, lang: str) -> str | None:
    """Pick the string for `lang`, falling back to the other language when missing."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if lang in value:
        return value[lang]
    return next(iter(value.values()))


def format_date(value: Any, lang: str) -> str:
    if value is None:
        return ""
    if value == "present":
        return PRESENT[lang]
    year, month = _DATE.match(str(value)).groups()
    return f"{MONTHS[lang][int(month) - 1]} {year}" if month else year


def format_range(start: Any, end: Any, lang: str) -> str:
    a, b = format_date(start, lang), format_date(end, lang)
    if a and b and a != b:
        return f"{a} -- {b}"
    return a or b


def targets(data: dict[str, Any]) -> list[Target]:
    """Every (variant, language) pair the source file asks for."""
    return [
        Target(vid, lang)
        for vid, variant in data["variants"].items()
        for lang in variant.get("languages", list(LANGUAGES))
    ]


def _included(item: dict[str, Any], variant: str) -> bool:
    tags = item.get("tags")
    return tags is None or variant in tags


def resolve(data: dict[str, Any], target: Target) -> dict[str, Any]:
    """Turn the source into the exact content of one CV (strings only, already ordered)."""
    if target.variant not in data["variants"]:
        raise CVError("variants", f"unknown variant '{target.variant}'")
    variant = data["variants"][target.variant]
    lang = target.lang
    profile = data["profile"]
    limits = variant.get("limits") or {}

    out_sections = []
    for sid in variant["sections"]:
        section = data["sections"][sid]
        kind = section["kind"]
        items = [it for it in section.get("items", []) if _included(it, target.variant)]
        if sid in limits:
            items = items[: limits[sid]]
        if not items:
            continue
        heading = text(section.get("heading") or DEFAULT_HEADINGS[sid], lang)
        resolved = []
        for it in items:
            if kind == "text":
                resolved.append({"text": text(it["text"], lang)})
            elif kind == "entries":
                resolved.append({
                    "title": text(it["title"], lang),
                    "org": text(it.get("org"), lang),
                    "location": text(it.get("location"), lang),
                    "dates": format_range(it.get("start"), it.get("end"), lang),
                    "note": text(it.get("note"), lang),
                    "bullets": [text(b, lang) for b in it.get("bullets", []) or []],
                    "tech": list(it.get("tech", []) or []),
                })
            elif kind == "skills":
                resolved.append({"group": text(it["group"], lang), "skills": [text(s, lang) for s in it["items"]]})
            elif kind == "languages":
                resolved.append({"name": text(it["name"], lang), "level": text(it["level"], lang)})
        out_sections.append({"id": sid, "kind": kind, "heading": heading, "rows": resolved})

    return {
        "lang": lang,
        "variant": target.variant,
        "name": text(profile["name"], lang),
        "headline": text(variant.get("headline") or profile.get("headline"), lang),
        "email": profile.get("email"),
        "phone": profile.get("phone"),
        "location": text(profile.get("location"), lang),
        "links": [{"label": text(l.get("label"), lang) or l["url"], "url": l["url"]}
                  for l in profile.get("links", []) or []],
        "sections": out_sections,
    }
