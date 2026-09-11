"""Analytics export routes."""

import logging
from io import BytesIO

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger(__name__)


class CandidateItem(BaseModel):
    id: int | str | None = None
    name: str | None = None
    role: str | None = None
    status: str | None = None
    score: str | int | float | None = None
    risk: str | None = None


class AnalyticsPDFRequest(BaseModel):
    """Same shape as the data passed to exportAnalyticsCSV()."""

    candidates: list[CandidateItem] = []
    stats: dict | None = None
    faults: dict | None = None


def create_analytics_routes() -> APIRouter:
    """Create analytics export routes."""

    router = APIRouter()

    @router.post("/analytics/export/pdf")
    async def export_analytics_pdf(request: AnalyticsPDFRequest):
        """Generate a downloadable PDF report from analytics data."""
        try:
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            styles = getSampleStyleSheet()
            elements = []

            elements.append(Paragraph("Analytics Report", styles["Title"]))
            elements.append(Spacer(1, 12))

            if request.candidates:
                elements.append(Paragraph("Candidates", styles["Heading2"]))
                table_data = [["Name", "Role", "Status", "Score", "Risk"]]
                for c in request.candidates:
                    table_data.append(
                        [
                            c.name or "-",
                            c.role or "-",
                            c.status or "-",
                            str(c.score) if c.score not in (None, "") else "-",
                            c.risk or "-",
                        ]
                    )

                table = Table(table_data, hAlign="LEFT")
                table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#6366f1")),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                            ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ]
                    )
                )
                elements.append(table)
                elements.append(Spacer(1, 20))

            if request.stats:
                elements.append(Paragraph("Session Statistics", styles["Heading2"]))
                for key, value in request.stats.items():
                    elements.append(
                        Paragraph(f"<b>{key}:</b> {value}", styles["Normal"])
                    )
                elements.append(Spacer(1, 20))

            if request.faults:
                elements.append(Paragraph("Fault Statistics", styles["Heading2"]))
                for key, value in request.faults.items():
                    elements.append(
                        Paragraph(f"<b>{key}:</b> {value}", styles["Normal"])
                    )

            if not request.candidates and not request.stats and not request.faults:
                elements.append(Paragraph("No data to export.", styles["Normal"]))

            doc.build(elements)
            buffer.seek(0)

            return StreamingResponse(
                buffer,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": "attachment; filename=analytics_report.pdf"
                },
            )

        except Exception as e:
            logger.error(f"Error generating analytics PDF: {e!s}")
            raise HTTPException(status_code=500, detail="Error generating PDF report")

    return router
