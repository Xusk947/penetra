"""Custom HTTP routes for report retrieval.

This Starlette app is mounted by the LangGraph dev server via the
``http.app`` key in ``langgraph.json``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import anyio
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, PlainTextResponse
from starlette.routing import Route

from agents.common.config import Settings
from agents.common.models import Finding
from agents.reporter.render import (
    build_report_markdown,
    localize_report,
    resolve_language,
)
from agents.reporter.trace import render_finding_trace
from db.reports import (
    SessionLocal,
    delete_report,
    get_report,
    init_db,
    list_reports,
    set_report_verified,
    update_pdf_path,
    update_report_content,
)
from services.pdf_renderer import arender_markdown_to_pdf

# Ensure the reports table exists before the first request.
init_db()

_BACKEND_DIR = Path(__file__).resolve().parent
_PDF_DIR = _BACKEND_DIR / "reports" / "pdfs"


def _pdf_path_for_report(report_id: str) -> Path:
    return _PDF_DIR / f"{report_id}.pdf"


def _report_to_dict(report: object) -> dict:
    return {
        "id": report.id,
        "thread_id": report.thread_id,
        "run_id": report.run_id,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "scope": report.scope,
        "focus": report.focus,
        "language": report.language,
        "title": report.title,
        "pdf_path": report.pdf_path,
        "finding_reports": report.finding_reports,
        "findings_count": report.findings_count,
        "request_prompt": report.request_prompt,
        "verified": bool(report.verified),
        "verified_at": report.verified_at.isoformat() if report.verified_at else None,
    }


def _fetch_report(report_id: str) -> dict[str, Any] | None:
    """Fetch a report and return it as a plain dict outside the request loop."""
    with SessionLocal() as session:
        report = get_report(session, report_id)
        if report is None:
            return None
        data = _report_to_dict(report)
        data["markdown"] = report.markdown
        data["findings"] = report.findings
        return data


def _inject_verified_banner(markdown: str, verified_at: str | None) -> str:
    """Insert the Admin Team verification banner right under the report title."""
    stamp = f" ({verified_at})" if verified_at else ""
    banner = f"> **Official report — manually verified by Admin Team{stamp}**"
    first, _, rest = markdown.partition("\n")
    return f"{first}\n\n{banner}\n{rest}"


def _with_verified_banner(report: dict[str, Any]) -> str:
    """Return the report markdown with the verification banner if verified."""
    markdown = report["markdown"]
    if report.get("verified"):
        markdown = _inject_verified_banner(markdown, report.get("verified_at"))
    return markdown


def _invalidate_pdfs(report_id: str, pdf_path: str | None) -> None:
    """Delete cached PDFs so they are regenerated with fresh content."""
    paths = {_pdf_path_for_report(report_id)}
    if pdf_path:
        paths.add(Path(pdf_path))
    for path in paths:
        path.unlink(missing_ok=True)


def _fetch_reports(
    *,
    thread_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """List reports and return them as plain dicts."""
    with SessionLocal() as session:
        reports = list_reports(
            session, thread_id=thread_id, limit=limit, offset=offset
        )
        return [_report_to_dict(r) for r in reports]


def _set_pdf_path(report_id: str, pdf_path: str) -> None:
    """Update the stored PDF path for a report."""
    with SessionLocal() as session:
        update_pdf_path(session, report_id, pdf_path)


async def _ensure_pdf(report_data: dict[str, Any]) -> Path:
    """Return an existing PDF path or generate a styled one from markdown."""
    pdf_path = _pdf_path_for_report(report_data["id"])
    if report_data.get("pdf_path"):
        existing = Path(report_data["pdf_path"])
        if await anyio.to_thread.run_sync(existing.is_file):
            return existing

    await arender_markdown_to_pdf(
        report_data["markdown"],
        pdf_path,
        title=report_data.get("title") or "Pentest report",
        scope=report_data.get("scope") or [],
        findings_count=report_data.get("findings_count") or 0,
        created_at=report_data.get("created_at"),
    )

    str_path = str(pdf_path)
    if report_data.get("pdf_path") != str_path:
        await anyio.to_thread.run_sync(_set_pdf_path, report_data["id"], str_path)

    return pdf_path


def list_reports_endpoint(request: Request) -> JSONResponse:
    """List reports, optionally filtered by thread ID."""
    thread_id = request.query_params.get("thread_id")
    limit = max(1, min(100, int(request.query_params.get("limit", "100"))))
    offset = max(0, int(request.query_params.get("offset", "0")))
    reports = _fetch_reports(thread_id=thread_id, limit=limit, offset=offset)
    return JSONResponse({"reports": reports})


def get_report_endpoint(request: Request) -> JSONResponse:
    """Fetch a single report by ID (markdown included)."""
    report_id = request.path_params["report_id"]
    report = _fetch_report(report_id)
    if report is None:
        return JSONResponse({"detail": "Report not found"}, status_code=404)
    return JSONResponse(report)


def delete_report_endpoint(request: Request) -> JSONResponse:
    """Delete a report and its associated files."""
    report_id = request.path_params["report_id"]
    with SessionLocal() as session:
        report = get_report(session, report_id)
        if report is None:
            return JSONResponse({"detail": "Report not found"}, status_code=404)

        if report.pdf_path:
            Path(report.pdf_path).unlink(missing_ok=True)
        for path in (report.finding_reports or {}).values():
            Path(path).unlink(missing_ok=True)

        delete_report(session, report_id)
    return JSONResponse({"deleted": report_id})


async def download_report_endpoint(request: Request):
    """Download a report as markdown or PDF.

    Use ``?format=md`` for a ``.md`` attachment (default) or ``?format=pdf``
    for a styled PDF attachment. PDFs are generated on demand if needed.
    """
    report_id = request.path_params["report_id"]
    fmt = request.query_params.get("format", "md").lower()

    report = await anyio.to_thread.run_sync(_fetch_report, report_id)
    if report is None:
        return JSONResponse({"detail": "Report not found"}, status_code=404)

    report["markdown"] = _with_verified_banner(report)

    if fmt == "pdf":
        pdf_path = await _ensure_pdf(report)
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=f"report_{report_id}.pdf",
        )

    return PlainTextResponse(
        report["markdown"],
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="report_{report_id}.md"'
        },
    )


async def view_pdf_endpoint(request: Request):
    """Return the styled PDF for a report (inline, generated on demand)."""
    report_id = request.path_params["report_id"]

    report = await anyio.to_thread.run_sync(_fetch_report, report_id)
    if report is None:
        return JSONResponse({"detail": "Report not found"}, status_code=404)

    report["markdown"] = _with_verified_banner(report)
    pdf_path = await _ensure_pdf(report)
    return FileResponse(pdf_path, media_type="application/pdf")


async def prepare_pdf_endpoint(request: Request) -> JSONResponse:
    """Regenerate and store the styled PDF for a report."""
    report_id = request.path_params["report_id"]

    report = await anyio.to_thread.run_sync(_fetch_report, report_id)
    if report is None:
        return JSONResponse({"detail": "Report not found"}, status_code=404)

    report["markdown"] = _with_verified_banner(report)
    pdf_path = _pdf_path_for_report(report_id)
    await arender_markdown_to_pdf(
        report["markdown"],
        pdf_path,
        title=report.get("title") or "Pentest report",
        scope=report.get("scope") or [],
        findings_count=report.get("findings_count") or 0,
        created_at=report.get("created_at"),
    )
    await anyio.to_thread.run_sync(_set_pdf_path, report_id, str(pdf_path))

    return JSONResponse({"report_id": report_id, "pdf_path": str(pdf_path)})


async def update_report_endpoint(request: Request) -> JSONResponse:
    """Replace a report's findings (manual Admin Team edit).

    The request body is ``{"findings": [...]}``; the markdown report and the
    per-finding trace files are rebuilt from the structured findings, and any
    cached PDF is invalidated so it regenerates with fresh content. The rebuilt
    report is re-localized into the report's stored language (e.g. ru/uz), so
    manual edits keep the original report language; if translation is
    unavailable the report falls back to English.
    """
    report_id = request.path_params["report_id"]
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"detail": "Invalid JSON body"}, status_code=400)

    raw_findings = body.get("findings")
    if not isinstance(raw_findings, list):
        return JSONResponse({"detail": "findings must be a list"}, status_code=400)

    try:
        findings = [Finding.model_validate(item) for item in raw_findings]
    except Exception as exc:
        return JSONResponse({"detail": f"Invalid findings: {exc}"}, status_code=400)

    def _update() -> dict[str, Any] | None:
        with SessionLocal() as session:
            report = get_report(session, report_id)
            if report is None:
                return None

            scope = report.scope or []
            markdown = build_report_markdown(findings, scope)
            language = resolve_language(report.language)
            if language != "en":
                markdown = localize_report(markdown, language)

            findings_dir = Path(Settings().reports_dir) / "findings"
            findings_dir.mkdir(parents=True, exist_ok=True)
            finding_reports: dict[str, str] = {}
            new_ids = {finding.id for finding in findings}
            for finding in findings:
                trace_path = findings_dir / f"{finding.id}.md"
                trace_path.write_text(render_finding_trace(finding), encoding="utf-8")
                finding_reports[finding.id] = str(trace_path)
            for old_id, old_path in (report.finding_reports or {}).items():
                if old_id not in new_ids:
                    Path(old_path).unlink(missing_ok=True)

            _invalidate_pdfs(report.id, report.pdf_path)
            updated = update_report_content(
                session,
                report_id,
                findings=[finding.model_dump() for finding in findings],
                markdown=markdown,
                finding_reports=finding_reports,
            )
            return _report_to_dict(updated) if updated else None

    data = await anyio.to_thread.run_sync(_update)
    if data is None:
        return JSONResponse({"detail": "Report not found"}, status_code=404)
    return JSONResponse(data)


async def verify_report_endpoint(request: Request) -> JSONResponse:
    """Mark/unmark a report as manually verified by the Admin Team."""
    report_id = request.path_params["report_id"]
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"detail": "Invalid JSON body"}, status_code=400)

    verified = bool(body.get("verified"))

    def _update() -> dict[str, Any] | None:
        with SessionLocal() as session:
            report = get_report(session, report_id)
            if report is None:
                return None
            _invalidate_pdfs(report.id, report.pdf_path)
            updated = set_report_verified(session, report_id, verified)
            return _report_to_dict(updated) if updated else None

    data = await anyio.to_thread.run_sync(_update)
    if data is None:
        return JSONResponse({"detail": "Report not found"}, status_code=404)
    return JSONResponse(data)


routes = [
    Route("/reports", list_reports_endpoint, methods=["GET"]),
    Route("/reports/{report_id}", get_report_endpoint, methods=["GET"]),
    Route("/reports/{report_id}", update_report_endpoint, methods=["PATCH"]),
    Route("/reports/{report_id}", delete_report_endpoint, methods=["DELETE"]),
    Route("/reports/{report_id}/download", download_report_endpoint, methods=["GET"]),
    Route("/reports/{report_id}/pdf", view_pdf_endpoint, methods=["GET"]),
    Route("/reports/{report_id}/pdf", prepare_pdf_endpoint, methods=["POST"]),
    Route("/reports/{report_id}/verify", verify_report_endpoint, methods=["POST"]),
]

app = Starlette(routes=routes)
