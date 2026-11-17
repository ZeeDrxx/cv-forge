# CV Forge

**One YAML file → every CV you need.** Keep each fact once, then generate targeted LaTeX CVs per
application type (general, end-of-studies internship, master's…) and per language (English, French).
Build locally, in Docker, or upload the generated project to Overleaf.

```
examples/cv.yaml ──► cvforge build ──► build/cv-general-en.pdf
                                       build/cv-general-fr.pdf
                                       build/cv-internship-en.pdf
                                       build/cv-internship-fr.pdf
                                       build/cv-masters-en.pdf
                                       build/cv-*.overleaf.zip   (with --overleaf)
```

## Why

Keeping a French CV, an English CV and a "master's application" CV in sync by hand means
the same bullet gets edited three times and drifts. CV Forge treats the CV like code:

- **One source of truth.** Experience, projects and skills are written once.
- **Variants, not copies.** A variant chooses which sections appear, in what order, and how many items each one keeps. Items carry `tags` to show up only where they matter.
- **Translations next to each other.** Every string is either plain text or `{en: …, fr: …}`. A missing translation falls back to the other language instead of breaking the build.
- **Safe LaTeX.** Everything from YAML is escaped (`&`, `%`, `_`, `#` …), with a tiny markdown subset: `**bold**` and `_italic_`.
- **Errors that point at the line.** `sections.experience.items[0].start: expected YYYY, YYYY-MM or 'present'`.

## Quick start

```bash
# Python 3.10+
pip install -e .
cvforge validate examples/cv.yaml
cvforge build examples/cv.yaml --overleaf      # needs tectonic or pdflatex on PATH
cvforge build examples/cv.yaml --engine none   # only writes the .tex files
```

### With Docker (no LaTeX install needed)

```bash
docker compose run --rm cvforge build examples/cv.yaml --overleaf
```

The image ships [Tectonic](https://tectonic-typesetting.github.io), a self-contained LaTeX engine.
Downloaded TeX packages are cached in a named volume, so only the first build is slow.

### With Overleaf

Run with `--overleaf`, then in Overleaf choose **New Project → Upload Project** and pick
`build/cv-<variant>-<lang>.overleaf.zip`. The class works with Overleaf's default pdfLaTeX compiler,
and with XeLaTeX / LuaLaTeX.

## The source file

```yaml
profile:
  name: Sam Rivera
  headline: { en: Software engineering student, fr: Élève ingénieur logiciel }
  email: sam.rivera@example.com

variants:
  general:    { sections: [summary, experience, projects, education, skills, languages] }
  internship: { sections: [summary, experience, projects, skills, education], limits: { projects: 3 } }
  masters:    { sections: [summary, education, projects, experience], languages: [en] }

sections:
  experience:
    kind: entries                # text | entries | skills | languages
    items:
      - title: { en: Backend Engineering Intern, fr: Stagiaire ingénieur backend }
        org: Northwind Logistics
        start: 2026-06           # YYYY, YYYY-MM or present
        end: 2026-09
        tags: [general, internship]   # omit to include everywhere
        bullets:
          - en: Rebuilt the order API in **FastAPI**; p95 latency 480 → 120 ms.
            fr: Refonte de l'API commandes en **FastAPI** ; latence p95 480 → 120 ms.
        tech: [Python, FastAPI, PostgreSQL]
```

See [`examples/cv.yaml`](examples/cv.yaml) for a complete file with all four section kinds.

| Field | Meaning |
|---|---|
| `variants.<id>.sections` | Section ids, in print order |
| `variants.<id>.limits` | Max items per section, e.g. `{ projects: 3 }` |
| `variants.<id>.headline` | Overrides the profile headline for this variant |
| `variants.<id>.languages` | Which languages to build (default `[en, fr]`) |
| `items[].tags` | Variants an item belongs to (default: all) |

## How it works

```
cv.yaml ─► model.load()      parse + validate, errors carry the field path
        ─► model.resolve()   (variant, language) → plain ordered strings
        ─► render.render_tex()  Jinja2 with LaTeX-safe delimiters ((( ))) / ((* *))
        ─► render.compile_pdf() tectonic or pdflatex
```

- `src/cvforge/templates/cvforge.cls`: the layout (one column, A4, TeX Gyre Heros). It picks fonts by engine, so the same file compiles on Overleaf and in Tectonic.
- `src/cvforge/templates/cv.tex.j2`: the document template. It uses `(((var)))` and `((* block *))` so LaTeX braces never clash with Jinja.

## Development

```bash
pip install -e ".[dev]"
pytest
```

CI runs the tests and builds every example PDF with Tectonic. The PDFs are attached to each run as artifacts.

## License

MIT
