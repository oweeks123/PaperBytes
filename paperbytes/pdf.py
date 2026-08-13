"""Server-side PDF generation for an article's summary + critical appraisal.

``build_summary_pdf`` is pure (dict in, bytes out) so it can be unit-tested
without a running server. The layout is a portfolio-friendly one-pager: title,
metadata, AI summary, the PICO/appraisal table, and an outcomes/statistics table.
"""

from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

_ACCENT = colors.HexColor("#1f6feb")
_MUTED = colors.HexColor("#555555")
_LINE = colors.HexColor("#cfd7df")


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("t", parent=base["Title"], fontSize=15, leading=19, spaceAfter=4),
        "meta": ParagraphStyle("m", parent=base["Normal"], fontSize=8.5, textColor=_MUTED, leading=12),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontSize=11, textColor=_ACCENT, spaceBefore=10, spaceAfter=4),
        "body": ParagraphStyle("b", parent=base["Normal"], fontSize=9.5, leading=13),
        "cell": ParagraphStyle("c", parent=base["Normal"], fontSize=8.5, leading=11),
        "cellhead": ParagraphStyle("ch", parent=base["Normal"], fontSize=8.5, leading=11, textColor=colors.white),
    }


def _kv_table(rows: list[tuple[str, str]], styles: dict[str, ParagraphStyle]) -> Table:
    data = [
        [Paragraph(f"<b>{k}</b>", styles["cell"]), Paragraph(v or "—", styles["cell"])]
        for k, v in rows
    ]
    t = Table(data, colWidths=[38 * mm, 132 * mm])
    t.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, -1), 0.4, _LINE),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f2f5f8")),
            ]
        )
    )
    return t


def _outcomes_table(outcomes: list[dict[str, Any]], styles: dict[str, ParagraphStyle]) -> Table:
    header = ["Outcome", "Measure", "Value", "95% CI", "p"]
    data: list[list[Any]] = [[Paragraph(f"<b>{h}</b>", styles["cellhead"]) for h in header]]
    for o in outcomes:
        data.append(
            [
                Paragraph(str(o.get("name") or "—"), styles["cell"]),
                Paragraph(str(o.get("measure") or "—"), styles["cell"]),
                Paragraph(str(o.get("value") or "—"), styles["cell"]),
                Paragraph(str(o.get("confidence_interval") or "—"), styles["cell"]),
                Paragraph(str(o.get("p_value") or "—"), styles["cell"]),
            ]
        )
    t = Table(data, colWidths=[54 * mm, 24 * mm, 28 * mm, 40 * mm, 24 * mm], repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _ACCENT),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.4, _LINE),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f9fb")]),
            ]
        )
    )
    return t


def build_summary_pdf(data: dict[str, Any]) -> bytes:
    """Render an article's summary + appraisal into a PDF and return the bytes.

    ``data`` mirrors the /random payload: title, journal, authors, publication_date,
    pmid, doi, pubmed_url, summary, specialties (list[str]), and appraisal (dict with
    study_design, population, intervention, comparator, risk_of_bias,
    level_of_evidence, limitations, outcomes[list]).
    """
    styles = _styles()
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm, bottomMargin=18 * mm,
        title=f"PaperBytes appraisal — PMID {data.get('pmid', '')}",
    )
    appraisal = data.get("appraisal") or {}
    specialties = ", ".join(data.get("specialties") or []) or "—"
    authors = data.get("authors") or []
    author_str = ", ".join(authors[:6]) + (" et al." if len(authors) > 6 else "")

    meta_bits = [
        data.get("journal"),
        data.get("publication_date"),
        f"PMID {data.get('pmid')}" if data.get("pmid") else None,
        f"doi:{data.get('doi')}" if data.get("doi") else None,
    ]
    meta_line = " · ".join(str(b) for b in meta_bits if b)

    flow: list[Any] = [
        Paragraph(str(data.get("title") or "Untitled"), styles["title"]),
        Paragraph(meta_line, styles["meta"]),
    ]
    if author_str:
        flow.append(Paragraph(author_str, styles["meta"]))
    flow.append(Paragraph(f'<link href="{data.get("pubmed_url", "")}">{data.get("pubmed_url", "")}</link>', styles["meta"]))

    flow.append(Paragraph("AI summary", styles["h2"]))
    flow.append(Paragraph(str(data.get("summary") or "—"), styles["body"]))

    flow.append(Paragraph("Critical appraisal", styles["h2"]))
    flow.append(
        _kv_table(
            [
                ("Study design", str(appraisal.get("study_design") or "")),
                ("Population", str(appraisal.get("population") or "")),
                ("Intervention", str(appraisal.get("intervention") or "")),
                ("Comparator", str(appraisal.get("comparator") or "")),
                ("Risk of bias", str(appraisal.get("risk_of_bias") or "")),
                ("Level of evidence", str(appraisal.get("level_of_evidence") or "")),
                ("Limitations", str(appraisal.get("limitations") or "")),
                ("Specialties", specialties),
            ],
            styles,
        )
    )

    outcomes = appraisal.get("outcomes") or []
    if outcomes:
        flow.append(Paragraph("Reported statistics", styles["h2"]))
        flow.append(_outcomes_table(outcomes, styles))

    flow.append(Spacer(1, 10 * mm))
    stamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    flow.append(
        Paragraph(
            f"Generated by PaperBytes on {stamp}. AI-generated summary/appraisal — verify against the source before clinical or portfolio use.",
            styles["meta"],
        )
    )

    doc.build(flow)
    return buf.getvalue()
