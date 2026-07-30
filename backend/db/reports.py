"""Report persistence backed by SQLite/SQLAlchemy."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    create_engine,
    func,
)
from sqlalchemy.orm import Session, declarative_base, sessionmaker

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_URL = f"sqlite:///{DATA_DIR / 'reports.sqlite'}"

Base = declarative_base()
engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Report(Base):
    """A pentest report tied to a chat thread."""

    __tablename__ = "reports"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    thread_id = Column(String, nullable=True, index=True)
    run_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    scope = Column(JSON, nullable=True)
    focus = Column(String, nullable=True)
    language = Column(String, nullable=True)
    title = Column(String, nullable=True)
    markdown = Column(Text, nullable=False)
    pdf_path = Column(String, nullable=True)
    finding_reports = Column(JSON, nullable=True)
    findings_count = Column(Integer, default=0)
    request_prompt = Column(Text, nullable=True)
    findings = Column(JSON, nullable=True)
    verified = Column(Boolean, default=False, nullable=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)


# Columns added after the initial schema; created via ALTER TABLE for
# existing SQLite databases (create_all does not alter existing tables).
_LATE_COLUMNS = {
    "findings": "findings JSON",
    "verified": "verified BOOLEAN DEFAULT 0 NOT NULL",
    "verified_at": "verified_at DATETIME",
}


def init_db() -> None:
    """Create the reports tables if they do not exist."""
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        existing = {
            row[1] for row in conn.exec_driver_sql("PRAGMA table_info(reports)")
        }
        for name, ddl in _LATE_COLUMNS.items():
            if name not in existing:
                conn.exec_driver_sql(f"ALTER TABLE reports ADD COLUMN {ddl}")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def save_report(
    session: Session,
    markdown: str,
    *,
    thread_id: str | None = None,
    run_id: str | None = None,
    scope: list[str] | None = None,
    focus: str | None = None,
    language: str | None = None,
    title: str | None = None,
    pdf_path: str | None = None,
    finding_reports: dict[str, str] | None = None,
    findings_count: int = 0,
    request_prompt: str | None = None,
    findings: list[dict[str, Any]] | None = None,
) -> Report:
    """Persist a new report and return the model instance."""
    report = Report(
        id=str(uuid.uuid4()),
        thread_id=thread_id,
        run_id=run_id,
        scope=scope if scope else None,
        focus=focus,
        language=language,
        title=title or "Pentest report",
        markdown=markdown,
        pdf_path=pdf_path,
        finding_reports=finding_reports,
        findings_count=findings_count,
        request_prompt=request_prompt,
        findings=findings,
    )
    session.add(report)
    session.commit()
    session.refresh(report)
    return report


def get_report(session: Session, report_id: str) -> Report | None:
    """Fetch a report by its ID."""
    return session.query(Report).filter(Report.id == report_id).first()


def update_pdf_path(session: Session, report_id: str, pdf_path: str) -> Report | None:
    """Update the PDF path for an existing report."""
    report = get_report(session, report_id)
    if report is None:
        return None
    report.pdf_path = pdf_path
    session.commit()
    session.refresh(report)
    return report


def update_report_content(
    session: Session,
    report_id: str,
    *,
    findings: list[dict[str, Any]],
    markdown: str,
    finding_reports: dict[str, str] | None = None,
) -> Report | None:
    """Replace a report's findings/markdown after a manual edit."""
    report = get_report(session, report_id)
    if report is None:
        return None
    report.findings = findings
    report.markdown = markdown
    report.findings_count = len(findings)
    if finding_reports is not None:
        report.finding_reports = finding_reports
    report.pdf_path = None
    session.commit()
    session.refresh(report)
    return report


def set_report_verified(
    session: Session, report_id: str, verified: bool
) -> Report | None:
    """Mark/unmark a report as manually verified by the Admin Team."""
    report = get_report(session, report_id)
    if report is None:
        return None
    report.verified = verified
    report.verified_at = _now() if verified else None
    report.pdf_path = None
    session.commit()
    session.refresh(report)
    return report


def delete_report(session: Session, report_id: str) -> bool:
    """Delete a report by its ID."""
    report = get_report(session, report_id)
    if report is None:
        return False
    session.delete(report)
    session.commit()
    return True


def list_reports(
    session: Session,
    *,
    thread_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Report]:
    """List reports, optionally filtered by thread ID."""
    query = session.query(Report)
    if thread_id:
        query = query.filter(Report.thread_id == thread_id)
    return (
        query.order_by(Report.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
