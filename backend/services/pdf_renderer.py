"""Render markdown reports as styled PDFs using the frontend fonts/CSS.

Uses Playwright to convert an HTML page (built from the markdown report and
using the same Manrope / JetBrains Mono variable fonts as the frontend) into a
PDF. The renderer exposes both an async entry point for the ASGI routes and a
sync wrapper for callers inside synchronous tool code.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape

import anyio
import markdown
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

_BACKEND_DIR = Path(__file__).resolve().parents[1]
_FRONTEND_DIR = _BACKEND_DIR.parent / "frontend"
_FONT_PACKAGES = {
    "Manrope Variable": _FRONTEND_DIR
    / "node_modules"
    / "@fontsource-variable"
    / "manrope",
    "JetBrains Mono Variable": _FRONTEND_DIR
    / "node_modules"
    / "@fontsource-variable"
    / "jetbrains-mono",
}


def _load_font_css(family: str, package_dir: Path) -> str:
    """Read a @fontsource-variable wght.css and rewrite file URLs to absolute."""
    wght_css = (package_dir / "wght.css").resolve()
    if not wght_css.exists():
        logger.warning("Font CSS not found for %s at %s", family, wght_css)
        return ""

    css_text = wght_css.read_text(encoding="utf-8")
    # Font files are referenced as ./files/<name>.woff2 inside the package.
    files_dir = (package_dir / "files").resolve()

    def _rewrite(match: re.Match) -> str:
        filename = match.group(1)
        font_file = files_dir / filename
        return f"url(file://{font_file.as_posix()})"

    return re.sub(r"url\(\./(files/[^\)]+)\)", _rewrite, css_text)


def _font_faces() -> str:
    """Return @font-face rules for all configured variable fonts."""
    parts: list[str] = []
    for family, package_dir in _FONT_PACKAGES.items():
        css = _load_font_css(family, package_dir)
        if css:
            parts.append(css)
        else:
            logger.warning("Could not load font faces for %s", family)
    return "\n".join(parts)


# Pre-compute the font-face CSS at import time so we do not perform filesystem
# resolution inside an async event loop (which triggers blocking-call warnings).
_FONT_FACES_CSS = _font_faces()


def _build_html(
    report_markdown: str,
    *,
    title: str,
    scope: list[str] | None = None,
    findings_count: int = 0,
    created_at: str | None = None,
) -> str:
    """Convert a markdown report into a styled HTML page."""
    md = markdown.Markdown(
        extensions=["fenced_code", "tables", "toc", "nl2br"],
    )
    html_body = md.convert(report_markdown)

    scope_text = ", ".join(scope) if scope else "N/A"
    meta_parts = [f"Scope: {escape(scope_text)}"]
    if findings_count:
        meta_parts.append(f"Findings: {findings_count}")
    if created_at:
        meta_parts.append(f"Generated: {escape(created_at)}")
    meta_line = " | ".join(meta_parts)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{escape(title)}</title>
<style>
{_FONT_FACES_CSS}

:root {{
  --background: oklch(1 0 0);
  --foreground: oklch(0.145 0 0);
  --card: oklch(1 0 0);
  --card-foreground: oklch(0.145 0 0);
  --primary: oklch(0.505 0.213 27.518);
  --primary-foreground: oklch(0.971 0.013 17.38);
  --secondary: oklch(0.967 0.001 286.375);
  --secondary-foreground: oklch(0.21 0.006 285.885);
  --muted: oklch(0.97 0 0);
  --muted-foreground: oklch(0.556 0 0);
  --accent: oklch(0.97 0 0);
  --accent-foreground: oklch(0.205 0 0);
  --destructive: oklch(0.577 0.245 27.325);
  --border: oklch(0.922 0 0);
  --radius: 0.625rem;
  --font-sans: 'Manrope Variable', 'Manrope', sans-serif;
  --font-mono: 'JetBrains Mono Variable', 'JetBrains Mono', monospace;
}}

@page {{
  size: A4;
  margin: 1.5cm;
}}

* {{
  box-sizing: border-box;
}}

body {{
  font-family: var(--font-sans);
  font-size: 11pt;
  line-height: 1.55;
  color: var(--foreground);
  background: var(--background);
  margin: 0;
  padding: 0;
}}

h1, h2, h3, h4 {{
  font-family: var(--font-sans);
  font-weight: 700;
  color: var(--foreground);
  margin-top: 1.2em;
  margin-bottom: 0.4em;
}}

h1 {{
  font-size: 22pt;
  border-bottom: 2px solid var(--primary);
  padding-bottom: 0.2em;
  margin-top: 0;
}}

h2 {{
  font-size: 16pt;
  color: var(--primary);
}}

h3 {{
  font-size: 13pt;
}}

h4 {{
  font-size: 11pt;
}}

p {{
  margin: 0.6em 0;
}}

.meta {{
  font-size: 9pt;
  color: var(--muted-foreground);
  margin-bottom: 1.5em;
}}

table {{
  width: 100%;
  border-collapse: collapse;
  margin: 1em 0;
  font-size: 9pt;
}}

th, td {{
  border: 1px solid var(--border);
  padding: 6px 8px;
  text-align: left;
  vertical-align: top;
}}

th {{
  background: var(--primary);
  color: var(--primary-foreground);
  font-weight: 700;
}}

tr:nth-child(even) {{
  background: var(--secondary);
}}

ul, ol {{
  margin: 0.6em 0;
  padding-left: 1.4em;
}}

li {{
  margin: 0.2em 0;
}}

code {{
  font-family: var(--font-mono);
  font-size: 9pt;
  background: var(--muted);
  padding: 2px 4px;
  border-radius: 4px;
}}

pre {{
  font-family: var(--font-mono);
  font-size: 8.5pt;
  background: var(--muted);
  padding: 10px;
  border-radius: var(--radius);
  overflow-wrap: break-word;
  white-space: pre-wrap;
}}

pre code {{
  background: transparent;
  padding: 0;
}}

blockquote {{
  border-left: 4px solid var(--primary);
  margin: 0.8em 0;
  padding-left: 1em;
  color: var(--muted-foreground);
}}

hr {{
  border: 0;
  border-top: 1px solid var(--border);
  margin: 1.5em 0;
}}

a {{
  color: var(--primary);
  text-decoration: underline;
}}

strong {{
  font-weight: 700;
  color: var(--foreground);
}}
</style>
</head>
<body>
  <h1>{escape(title)}</h1>
  <div class="meta">{meta_line}</div>
  {html_body}
</body>
</html>
"""


async def arender_markdown_to_pdf(
    report_markdown: str,
    output_path: Path,
    *,
    title: str = "Pentest report",
    scope: list[str] | None = None,
    findings_count: int = 0,
    created_at: str | None = None,
) -> Path:
    """Async entry point: render *report_markdown* to a styled PDF.

    Uses Playwright's async API so it can be awaited from ASGI routes without
    blocking the event loop. Writes the PDF to disk with async file I/O.
    """
    output_path = output_path.resolve()
    await anyio.to_thread.run_sync(
        lambda: output_path.parent.mkdir(parents=True, exist_ok=True)
    )

    html = _build_html(
        report_markdown,
        title=title,
        scope=scope,
        findings_count=findings_count,
        created_at=created_at,
    )

    tmp_path: Path | None = None
    try:
        fd, tmp_name = await anyio.to_thread.run_sync(
            lambda: tempfile.mkstemp(suffix=".html", dir=str(output_path.parent))
        )
        await anyio.to_thread.run_sync(os.close, fd)
        tmp_path = Path(tmp_name)
        async with await anyio.open_file(tmp_path, "w", encoding="utf-8") as f:
            await f.write(html)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(f"file://{tmp_path.as_posix()}", wait_until="networkidle")
            pdf_bytes = await page.pdf(
                format="A4",
                margin={"top": "1.5cm", "right": "1.5cm", "bottom": "1.5cm", "left": "1.5cm"},
                print_background=True,
            )
            await browser.close()

        async with await anyio.open_file(output_path, "wb") as f:
            await f.write(pdf_bytes)
    finally:
        if tmp_path:
            await anyio.to_thread.run_sync(lambda: tmp_path.unlink(missing_ok=True))

    logger.info("Rendered styled PDF report to %s", output_path)
    return output_path


def render_markdown_to_pdf(
    report_markdown: str,
    output_path: Path,
    *,
    title: str = "Pentest report",
    scope: list[str] | None = None,
    findings_count: int = 0,
    created_at: str | None = None,
) -> Path:
    """Sync wrapper around :func:`arender_markdown_to_pdf`.

    Intended for synchronous callers such as tool functions. Raises if called
    from inside an already running event loop.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(
            arender_markdown_to_pdf(
                report_markdown,
                output_path,
                title=title,
                scope=scope,
                findings_count=findings_count,
                created_at=created_at,
            )
        )
    else:
        # If we are already on an event loop, schedule the coroutine in the
        # background and wait for it. This should not happen for the current
        # sync tool callers, but defends against accidental nested invocation.
        return asyncio.run_coroutine_threadsafe(
            arender_markdown_to_pdf(
                report_markdown,
                output_path,
                title=title,
                scope=scope,
                findings_count=findings_count,
                created_at=created_at,
            ),
            loop,
        ).result()

