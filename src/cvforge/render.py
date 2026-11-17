"""Render resolved CVs to .tex and compile them to PDF."""

from __future__ import annotations

import shutil
import subprocess
import zipfile
from importlib import resources
from pathlib import Path
from typing import Any

import jinja2

from . import latex
from .model import Target, resolve

CLASS_FILE = "cvforge.cls"
TEMPLATE_FILE = "cv.tex.j2"


def _templates() -> resources.abc.Traversable:
    return resources.files("cvforge") / "templates"


def environment() -> jinja2.Environment:
    """Jinja with LaTeX-friendly delimiters so braces and % stay plain LaTeX."""
    env = jinja2.Environment(
        loader=jinja2.FunctionLoader(lambda name: (_templates() / name).read_text(encoding="utf-8")),
        block_start_string="((*",
        block_end_string="*))",
        variable_start_string="(((",
        variable_end_string=")))",
        comment_start_string="((=",
        comment_end_string="=))",
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=False,
        undefined=jinja2.StrictUndefined,
        keep_trailing_newline=True,
    )
    env.filters["tex"] = latex.escape
    env.filters["inline"] = latex.inline
    env.filters["texurl"] = latex.url
    env.globals["contact_line"] = contact_line
    return env


def contact_line(cv: dict[str, Any]) -> str:
    """Location · email · phone · links, as one LaTeX line."""
    parts = []
    if cv.get("location"):
        parts.append(latex.escape(cv["location"]))
    if cv.get("email"):
        parts.append(rf"\href{{mailto:{latex.url(cv['email'])}}}{{{latex.escape(cv['email'])}}}")
    if cv.get("phone"):
        parts.append(latex.escape(cv["phone"]))
    for link in cv.get("links", []):
        parts.append(rf"\href{{{latex.url(link['url'])}}}{{{latex.escape(link['label'])}}}")
    return r"\cvsep ".join(parts)


def render_tex(cv: dict[str, Any]) -> str:
    return environment().get_template(TEMPLATE_FILE).render(cv=cv)


def class_source() -> str:
    return (_templates() / CLASS_FILE).read_text(encoding="utf-8")


def write_target(data: dict[str, Any], target: Target, out_dir: Path) -> Path:
    """Write <slug>/main.tex and the class file. Returns the .tex path."""
    folder = out_dir / target.slug
    folder.mkdir(parents=True, exist_ok=True)
    tex = folder / "main.tex"
    tex.write_text(render_tex(resolve(data, target)), encoding="utf-8")
    (folder / CLASS_FILE).write_text(class_source(), encoding="utf-8")
    return tex


def overleaf_zip(tex: Path) -> Path:
    """Zip main.tex + class: upload it via Overleaf → New Project → Upload Project."""
    archive = tex.parent.with_suffix(".overleaf.zip")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in (tex, tex.parent / CLASS_FILE):
            zf.write(f, f.name)
    return archive


class CompileError(RuntimeError):
    pass


def pick_engine(requested: str) -> str:
    if requested != "auto":
        return requested
    if shutil.which("tectonic"):
        return "tectonic"
    if shutil.which("pdflatex"):
        return "pdflatex"
    raise CompileError(
        "No LaTeX engine found. Install Tectonic (https://tectonic-typesetting.github.io), "
        "or build in Docker: docker compose run --rm cvforge build examples/cv.yaml"
    )


def compile_pdf(tex: Path, engine: str) -> Path:
    folder = tex.parent
    if engine == "tectonic":
        cmd = ["tectonic", "--keep-logs", "--outdir", ".", tex.name]
        runs = 1  # tectonic reruns itself as needed
    elif engine == "pdflatex":
        cmd = ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", tex.name]
        runs = 2
    else:
        raise CompileError(f"unknown engine '{engine}'")
    for _ in range(runs):
        proc = subprocess.run(cmd, cwd=folder, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if proc.returncode != 0:
            tail = "\n".join((proc.stdout + proc.stderr).splitlines()[-25:])
            raise CompileError(f"{engine} failed on {tex}:\n{tail}")
    pdf = tex.with_suffix(".pdf")
    final = folder.parent / f"{folder.name}.pdf"
    shutil.copyfile(pdf, final)
    return final
