"""Auto-generate API reference pages (one per module) from the source tree.

Run by mkdocs-gen-files at build time — nothing is written into the repo.
Add a new module under src/choreoai and it appears in the docs automatically.

Also builds:
  - reference/index.md  — section landing / table of modules (grouped by package)
  - reference/SUMMARY.md — literate nav (flattened under API reference, no extra
    top-level ``choreoai`` node)
"""
from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path

import mkdocs_gen_files

nav = mkdocs_gen_files.Nav()
root = Path(__file__).resolve().parent.parent
src = root / "src"

# (ident, doc_path_posix, is_package, source_path) collected while walking.
modules: list[tuple[str, str, bool, Path]] = []


def _first_doc_line(path: Path) -> str:
    """Return the first non-empty line of a module docstring, if any."""
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ""
    doc = ast.get_docstring(tree)
    if not doc:
        return ""
    for line in doc.strip().splitlines():
        line = line.strip()
        if line:
            return line
    return ""


for path in sorted(src.rglob("*.py")):
    module_path = path.relative_to(src).with_suffix("")
    doc_path = path.relative_to(src).with_suffix(".md")
    full_doc_path = Path("reference", doc_path)

    parts = tuple(module_path.parts)

    if parts[-1] == "__init__":
        parts = parts[:-1]
        doc_path = doc_path.with_name("index.md")
        full_doc_path = full_doc_path.with_name("index.md")
        is_package = True
    elif parts[-1] == "__main__":
        continue
    else:
        is_package = False

    # Skip private modules (leading underscore) and impl details.
    if not parts or any(p.startswith("_") for p in parts) or parts[-1].endswith("_impl"):
        continue

    # Flatten nav: drop the redundant nesting so agents / core / engine / …
    # sit directly under "API reference". Keep the package root as a sibling
    # entry so its page stays in the nav (strict build forbids orphans).
    if parts[0] == "choreoai" and len(parts) > 1:
        nav[parts[1:]] = doc_path.as_posix()
    else:
        nav[parts] = doc_path.as_posix()

    ident = ".".join(parts)
    modules.append((ident, doc_path.as_posix(), is_package, path))

    with mkdocs_gen_files.open(full_doc_path, "w") as fd:
        fd.write(f"# `{ident}`\n\n::: {ident}\n")

    mkdocs_gen_files.set_edit_path(full_doc_path, path.relative_to(root))


# --- Overview / section landing page -----------------------------------------
# Group modules by first package segment after ``choreoai`` (or "package root").
grouped: dict[str, list[tuple[str, str, Path]]] = defaultdict(list)
group_order: list[str] = []

for ident, doc_path_posix, _is_package, source_path in modules:
    parts = ident.split(".")
    if len(parts) == 1:
        group = "package root"
    else:
        group = parts[1]  # agents, core, engine, …
    if group not in grouped:
        group_order.append(group)
    grouped[group].append((ident, doc_path_posix, source_path))

lines: list[str] = [
    "# API reference\n",
    "\n",
    "Public modules of the `choreoai` package, grouped by top-level package. "
    "Pages are generated from source at build time — add a module under "
    "`src/choreoai` and it appears here automatically.\n",
    "\n",
]

for group in group_order:
    entries = grouped[group]
    heading = "`choreoai`" if group == "package root" else f"`choreoai.{group}`"
    lines.append(f"## {heading}\n\n")
    lines.append("| Module | Description |\n")
    lines.append("| --- | --- |\n")
    for ident, doc_path_posix, source_path in entries:
        summary = _first_doc_line(source_path).replace("|", "\\|")
        # Relative links from reference/index.md into the generated tree.
        lines.append(f"| [`{ident}`]({doc_path_posix}) | {summary} |\n")
    lines.append("\n")

with mkdocs_gen_files.open("reference/index.md", "w") as index_file:
    index_file.writelines(lines)

# Literate nav: index first so section-index + navigation.indexes make
# "API reference" open this overview (reference/ resolves, no 404).
# Title matches the H1 / section name so the tab and page title stay consistent.
with mkdocs_gen_files.open("reference/SUMMARY.md", "w") as nav_file:
    nav_file.write("* [API reference](index.md)\n")
    nav_file.writelines(nav.build_literate_nav())
