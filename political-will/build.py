"""Build political-will HTML pages from Markdown in content/.

Usage (from this directory):
  pip install -r requirements.txt
  python build.py

Edit content/*.md, then re-run build.py. Do not hand-edit the generated .html
pages (except styles.css / assets / includes).

Front matter (YAML-ish, simple key: value):
  title: Page heading / <title> base
  output: filename.html          (default: <stem>.html)
  body_class: map-page          (optional CSS class on <body>)
  parents: true                 (optional; adds Parent pages → Main page)
  extra_head: mermaid           (optional; injects includes/mermaid-head.html)

In Markdown body you can use:
  <!-- include: map-diagram.html -->
to splice a file from includes/ (useful for the Mermaid map).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import markdown
except ImportError:
    sys.stderr.write(
        "Missing dependency. Run:\n  pip install -r requirements.txt\n"
    )
    sys.exit(1)

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
INCLUDES = ROOT / "includes"
TEMPLATE = (ROOT / "template.html").read_text(encoding="utf-8")

FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", re.S)
INCLUDE_RE = re.compile(r"<!--\s*include:\s*([^\s]+)\s*-->")


def parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    match = FRONT_MATTER_RE.match(text)
    if not match:
        return {}, text
    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip()
    return meta, match.group(2)


def expand_includes(text: str) -> str:
    def repl(m: re.Match[str]) -> str:
        path = INCLUDES / m.group(1)
        if not path.is_file():
            raise FileNotFoundError(f"Include not found: {path}")
        return path.read_text(encoding="utf-8").rstrip("\n")

    return INCLUDE_RE.sub(repl, text)


def truthy(value: str | None) -> bool:
    return (value or "").lower() in {"1", "true", "yes", "y"}


def page_title(meta: dict[str, str]) -> str:
    title = meta.get("title", "Political Will Map")
    if truthy(meta.get("full_title")):
        return title
    if meta.get("output") == "index.html" or meta.get("slug") == "index":
        return title
    return f"{title} — Political Will Map"


def build_one(md_path: Path) -> Path:
    raw = md_path.read_text(encoding="utf-8")
    meta, body_md = parse_front_matter(raw)
    body_md = expand_includes(body_md)

    body_html = markdown.markdown(
        body_md,
        extensions=["extra", "sane_lists", "smarty"],
        output_format="html5",
    )

    if truthy(meta.get("parents")):
        body_html += (
            '\n<p class="parents">Parent pages: '
            '<a href="index.html">Main page</a></p>\n'
        )

    # Keep body as-is (no re-indent) so <pre class="mermaid"> source stays valid.
    body_block = body_html.strip() + "\n"

    extra = ""
    if meta.get("extra_head") == "mermaid":
        extra = (INCLUDES / "mermaid-head.html").read_text(encoding="utf-8")
        if not extra.endswith("\n"):
            extra += "\n"

    body_class = meta.get("body_class", "").strip()
    body_class_attr = f' class="{body_class}"' if body_class else ""

    html = (
        TEMPLATE.replace("{{title}}", page_title(meta))
        .replace("{{extra_head}}", extra)
        .replace("{{body_class_attr}}", body_class_attr)
        .replace("{{body}}", body_block)
    )

    out_name = meta.get("output") or f"{md_path.stem}.html"
    out_path = ROOT / out_name
    out_path.write_text(html, encoding="utf-8", newline="\n")
    return out_path


def main() -> None:
    if not CONTENT.is_dir():
        sys.stderr.write(f"Missing content directory: {CONTENT}\n")
        sys.exit(1)

    paths = sorted(CONTENT.glob("*.md"))
    if not paths:
        sys.stderr.write(f"No Markdown files in {CONTENT}\n")
        sys.exit(1)

    for md_path in paths:
        out = build_one(md_path)
        print(f"wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
