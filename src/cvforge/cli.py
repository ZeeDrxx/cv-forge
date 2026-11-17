"""cvforge command line: validate, list and build CVs from one YAML source."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .model import CVError, LANGUAGES, Target, load, targets
from .render import CompileError, compile_pdf, overleaf_zip, pick_engine, write_target


def _select(data: dict, variant: str | None, lang: str | None) -> list[Target]:
    chosen = [t for t in targets(data) if (variant is None or t.variant == variant)
              and (lang is None or t.lang == lang)]
    if not chosen:
        raise CVError("--variant/--lang", "no CV matches this selection")
    return chosen


def cmd_validate(args: argparse.Namespace) -> int:
    data = load(args.source)
    print(f"OK  {args.source}: {len(targets(data))} CVs ({', '.join(t.slug for t in targets(data))})")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    for t in targets(load(args.source)):
        print(t.slug)
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    data = load(args.source)
    out = Path(args.out)
    engine = None if args.engine == "none" else pick_engine(args.engine)
    for target in _select(data, args.variant, args.lang):
        tex = write_target(data, target, out)
        line = f"{target.slug:<22} {tex}"
        if args.overleaf:
            line += f"  overleaf: {overleaf_zip(tex)}"
        if engine:
            line += f"  pdf: {compile_pdf(tex, engine)}"
        print(line)
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="cvforge", description=__doc__)
    p.add_argument("--version", action="version", version=f"cvforge {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    v = sub.add_parser("validate", help="check a source file and report what it would build")
    v.add_argument("source")
    v.set_defaults(func=cmd_validate)

    l = sub.add_parser("list", help="list the CVs (variant × language) a source file defines")
    l.add_argument("source")
    l.set_defaults(func=cmd_list)

    b = sub.add_parser("build", help="render .tex files and, by default, compile them to PDF")
    b.add_argument("source")
    b.add_argument("-o", "--out", default="build", help="output folder (default: build)")
    b.add_argument("--variant", help="only this variant")
    b.add_argument("--lang", choices=LANGUAGES, help="only this language")
    b.add_argument("--engine", default="auto", choices=["auto", "tectonic", "pdflatex", "none"],
                   help="LaTeX engine; 'none' writes .tex only (default: auto)")
    b.add_argument("--overleaf", action="store_true", help="also write an Overleaf-ready .zip per CV")
    b.set_defaults(func=cmd_build)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        return args.func(args)
    except (CVError, CompileError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
