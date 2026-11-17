from pathlib import Path

import pytest
import yaml

from cvforge import latex
from cvforge.cli import main
from cvforge.model import CVError, Target, format_range, load, resolve, targets, validate
from cvforge.render import render_tex, write_target, overleaf_zip

EXAMPLE = Path(__file__).parent.parent / "examples" / "cv.yaml"


@pytest.fixture
def data():
    return load(EXAMPLE)


# ------------------------------------------------------------------ latex


def test_escape_every_special_character():
    assert latex.escape("100% & $5 #1 a_b {x} ~ ^ \\") == (
        r"100\% \& \$5 \#1 a\_b \{x\} \textasciitilde{} \textasciicircum{} \textbackslash{}"
    )


def test_inline_markdown_bold_and_italic():
    assert latex.inline("a **b & c** d") == r"a \textbf{b \& c} d"
    assert latex.inline("an _italic_ word") == r"an \textit{italic} word"


def test_inline_leaves_snake_case_alone():
    assert latex.inline("snake_case_name") == r"snake\_case\_name"


# ------------------------------------------------------------------ model


def test_example_defines_five_targets(data):
    assert [t.slug for t in targets(data)] == [
        "cv-general-en", "cv-general-fr", "cv-internship-en", "cv-internship-fr", "cv-masters-en",
    ]


def test_tags_filter_items_per_variant(data):
    general = resolve(data, Target("general", "en"))
    masters = resolve(data, Target("masters", "en"))
    titles = lambda cv, sid: [i["title"] for s in cv["sections"] if s["id"] == sid for i in s["rows"]]
    assert "Snake_case linter" in titles(general, "projects")
    assert "Snake_case linter" not in titles(masters, "projects")
    assert "Demand forecasting thesis" in titles(masters, "projects")


def test_limits_cap_section_length(data):
    cv = resolve(data, Target("internship", "en"))
    projects = next(s for s in cv["sections"] if s["id"] == "projects")
    assert len(projects["rows"]) == 3


def test_section_order_follows_variant(data):
    cv = resolve(data, Target("masters", "en"))
    assert [s["id"] for s in cv["sections"]] == ["summary", "education", "projects", "experience", "awards", "languages"]


def test_language_picks_translation_and_headings(data):
    fr = resolve(data, Target("general", "fr"))
    assert fr["sections"][1]["heading"] == "Expérience"
    assert fr["sections"][1]["rows"][0]["title"] == "Stagiaire ingénieur backend"


def test_missing_translation_falls_back(data):
    # the masters summary only exists in English
    cv = resolve(data, Target("masters", "fr"))
    assert cv["sections"][0]["rows"][0]["text"].startswith("Final-year student")


def test_dates_are_localised():
    assert format_range("2026-06", "2026-09", "en") == "Jun 2026 -- Sep 2026"
    assert format_range("2026-06", "present", "fr") == "juin 2026 -- présent"
    assert format_range(None, 2022, "en") == "2022"


@pytest.mark.parametrize("mutate, where", [
    (lambda d: d.pop("variants"), "<root>"),
    (lambda d: d["variants"]["general"]["sections"].append("hobbies"), "variants.general.sections"),
    (lambda d: d["sections"]["experience"]["items"][0].update(start="June 2026"), "sections.experience.items[0].start"),
    (lambda d: d["sections"]["skills"].update(kind="table"), "sections.skills.kind"),
    (lambda d: d["variants"]["masters"].update(languages=["de"]), "variants.masters.languages"),
    # `{ en: Lyon, France }` in YAML flow style silently becomes {en: Lyon, France: null}
    (lambda d: d["profile"].update(location={"en": "Lyon", "France": None}), "profile.location"),
])
def test_validation_points_at_the_bad_field(mutate, where):
    raw = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    mutate(raw)
    with pytest.raises(CVError) as err:
        validate(raw)
    assert err.value.where == where


# ------------------------------------------------------------------ rendering


def test_rendered_tex_is_escaped_and_complete(data):
    tex = render_tex(resolve(data, Target("general", "en")))
    assert tex.startswith("% !TEX program = pdflatex")
    assert r"\documentclass{cvforge}" in tex and tex.rstrip().endswith(r"\end{document}")
    assert r"100\% snake\_case" in tex
    assert r"\textbf{FastAPI}" in tex
    assert r"\href{mailto:sam.rivera@example.com}" in tex
    assert "(((" not in tex and "((*" not in tex


def test_write_target_and_overleaf_zip(data, tmp_path):
    import zipfile

    tex = write_target(data, Target("internship", "fr"), tmp_path)
    assert (tex.parent / "cvforge.cls").exists()
    with zipfile.ZipFile(overleaf_zip(tex)) as zf:
        assert sorted(zf.namelist()) == ["cvforge.cls", "main.tex"]


def test_cli_build_without_engine(tmp_path, capsys):
    assert main(["build", str(EXAMPLE), "-o", str(tmp_path), "--engine", "none", "--lang", "fr"]) == 0
    assert sorted(p.name for p in tmp_path.iterdir()) == ["cv-general-fr", "cv-internship-fr"]


def test_cli_reports_errors_cleanly(tmp_path, capsys):
    bad = tmp_path / "bad.yaml"
    bad.write_text("profile: {name: X}\nsections: {}\nvariants: {}\n", encoding="utf-8")
    assert main(["validate", str(bad)]) == 1
    assert "sections: expected a non-empty mapping" in capsys.readouterr().err
