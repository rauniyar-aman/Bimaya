"""On-the-fly PDF builders for customer policy documents.

Documents are rendered per-request from current data and streamed straight to
the customer — nothing is written to disk. Certificates carry PII (holder name,
document number, address), so keeping them in memory avoids persisting that PII
under ``MEDIA_ROOT``. The layout uses the Bimaya brand palette; the logo is not
in the repo, so the header is a text "BIMAYA" wordmark rather than an image.
"""

from io import BytesIO

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Brand palette — mirrors the Tailwind theme in Frontend/src/app/globals.css.
BRAND = colors.HexColor("#1E5FA8")
INK = colors.HexColor("#0F1F33")
MUTED = colors.HexColor("#5B6B7F")
GREEN = colors.HexColor("#27AE60")
GREEN_SOFT = colors.HexColor("#E9F8EF")
LINE = colors.HexColor("#E4EAF1")

_PAGE_MARGIN = 20 * mm
_CONTENT_WIDTH = A4[0] - 2 * _PAGE_MARGIN


def _styles():
    """Paragraph styles used across both documents."""
    return {
        "wordmark": ParagraphStyle(
            "wordmark",
            fontName="Helvetica-Bold",
            fontSize=26,
            leading=28,
            textColor=BRAND,
        ),
        "tagline": ParagraphStyle(
            "tagline", fontName="Helvetica", fontSize=9, leading=12, textColor=MUTED
        ),
        "title": ParagraphStyle(
            "title",
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=22,
            textColor=INK,
            spaceBefore=6,
        ),
        "intro": ParagraphStyle(
            "intro", fontName="Helvetica", fontSize=9.5, leading=14, textColor=MUTED
        ),
        "label": ParagraphStyle(
            "label", fontName="Helvetica", fontSize=8.5, leading=12, textColor=MUTED
        ),
        "value": ParagraphStyle(
            "value", fontName="Helvetica", fontSize=10.5, leading=14, textColor=INK
        ),
        "value_strong": ParagraphStyle(
            "value_strong",
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=INK,
        ),
        "chip": ParagraphStyle(
            "chip",
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            textColor=GREEN,
            alignment=TA_LEFT,
        ),
        "footer": ParagraphStyle(
            "footer", fontName="Helvetica", fontSize=8, leading=11, textColor=MUTED
        ),
    }


def _header(styles):
    """Wordmark + tagline + brand rule, shared by every document."""
    return [
        Paragraph("BIMAYA", styles["wordmark"]),
        Paragraph("Online insurance made easy", styles["tagline"]),
        HRFlowable(
            width="100%", thickness=2, color=BRAND, spaceBefore=8, spaceAfter=4
        ),
    ]


def _details_table(rows, styles):
    """A two-column label/value table with a light rule under each row."""
    data = [
        [
            Paragraph(label, styles["label"]),
            Paragraph(value or "—", styles.get(value_style, styles["value"])),
        ]
        for label, value, value_style in rows
    ]
    table = Table(data, colWidths=[45 * mm, _CONTENT_WIDTH - 45 * mm])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LINEBELOW", (0, 0), (-1, -1), 0.5, LINE),
            ]
        )
    )
    return table


def _status_chip(text, styles):
    """A small pill (e.g. ACTIVE / PAID) drawn as a single bordered cell."""
    chip = Table([[Paragraph(text, styles["chip"])]], colWidths=[26 * mm])
    chip.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 1, GREEN),
                ("BACKGROUND", (0, 0), (-1, -1), GREEN_SOFT),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return chip


def _money(value):
    """Format a Decimal amount as ``NPR 1,000,000.00``."""
    if value is None:
        return "—"
    return f"NPR {value:,.2f}"


def _date(value):
    return value.strftime("%d %b %Y") if value else "—"


def _build(story):
    """Render a flowable story to PDF bytes on an in-memory buffer."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=_PAGE_MARGIN,
        rightMargin=_PAGE_MARGIN,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="Bimaya document",
    )
    doc.build(story)
    return buffer.getvalue()


def render_certificate(purchase):
    """Build a Certificate of Insurance PDF for an issued ``PolicyPurchase``."""
    styles = _styles()
    policy = purchase.policy
    kyc = purchase.kyc

    holder_name = kyc.full_name if kyc else "—"
    if kyc and kyc.document_number:
        holder_doc = f"{kyc.get_document_type_display()} · {kyc.document_number}"
    else:
        holder_doc = "—"
    holder_address = kyc.permanent_address if kyc else "—"

    nominee = purchase.nominee_name or "—"
    if purchase.nominee_relationship:
        nominee = f"{nominee} ({purchase.nominee_relationship})"

    story = _header(styles)
    story += [
        Paragraph("Certificate of Insurance", styles["title"]),
        Spacer(1, 4),
        Paragraph(
            "This certifies that the policy described below has been issued "
            "through the Bimaya marketplace and is currently active.",
            styles["intro"],
        ),
        Spacer(1, 12),
        _details_table(
            [
                ("Policy", policy.name, "value"),
                ("Category", policy.category.name, "value"),
                ("Insurer", policy.provider.company_name, "value"),
                ("Policy number", purchase.policy_number, "value_strong"),
                ("Policyholder", holder_name, "value"),
                ("Identification", holder_doc, "value"),
                ("Address", holder_address, "value"),
                ("Sum assured", _money(policy.coverage_amount), "value_strong"),
                (
                    "Premium",
                    f"{_money(policy.premium)} · {policy.get_premium_frequency_display()}",
                    "value",
                ),
                (
                    "Cover period",
                    f"{_date(purchase.start_date)} to {_date(purchase.end_date)}",
                    "value",
                ),
                ("Nominee", nominee, "value"),
                ("Nominee contact", purchase.nominee_contact, "value"),
            ],
            styles,
        ),
        Spacer(1, 14),
        _status_chip("ACTIVE", styles),
        Spacer(1, 18),
        Paragraph(
            "This document is computer-generated and valid without a signature. "
            "Bimaya operates as an insurance marketplace; the policy is "
            f"underwritten by {policy.provider.company_name}. Generated on "
            f"{_date(timezone.localdate())}.",
            styles["footer"],
        ),
    ]
    return _build(story)


def render_receipt(payment):
    """Build a payment receipt PDF for a successful ``Payment``."""
    styles = _styles()
    purchase = payment.policy_purchase
    policy = purchase.policy
    kyc = purchase.kyc

    payer = (kyc.full_name if kyc else "") or getattr(
        purchase.customer, "full_name", ""
    ) or purchase.customer.email

    story = _header(styles)
    story += [
        Paragraph("Payment Receipt", styles["title"]),
        Spacer(1, 4),
        Paragraph(
            "Receipt for a premium payment made through the Bimaya marketplace.",
            styles["intro"],
        ),
        Spacer(1, 12),
        _details_table(
            [
                ("Receipt number", payment.gateway_transaction_id, "value"),
                (
                    "Paid on",
                    payment.paid_at.strftime("%d %b %Y, %I:%M %p")
                    if payment.paid_at
                    else "—",
                    "value",
                ),
                ("Paid by", payer, "value"),
                ("Policy", policy.name, "value"),
                ("Policy number", purchase.policy_number, "value"),
                ("Insurer", policy.provider.company_name, "value"),
                ("Payment method", payment.get_gateway_display(), "value"),
                ("Amount paid", _money(payment.amount), "value_strong"),
            ],
            styles,
        ),
        Spacer(1, 14),
        _status_chip("PAID", styles),
        Spacer(1, 18),
        Paragraph(
            "This document is computer-generated and valid without a signature. "
            f"Generated on {_date(timezone.localdate())}.",
            styles["footer"],
        ),
    ]
    return _build(story)
