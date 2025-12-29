from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from django.http import HttpResponse
import os
from django.conf import settings


def generate_invoice_pdf(invoice):
    # ──────────────────────────────────────────────────────────
    # PDF CONFIG
    # ──────────────────────────────────────────────────────────
    response = HttpResponse(content_type="application/pdf")
    response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.invoice_number}.pdf"'

    pdf = SimpleDocTemplate(
        response,
        pagesize=A4,
        rightMargin=30, leftMargin=30,
        topMargin=30, bottomMargin=18
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="InvoiceTitle", fontSize=22, leading=28, alignment=1, spaceAfter=20))
    styles.add(ParagraphStyle(name="Heading", fontSize=14, leading=16, spaceAfter=10, textColor=colors.HexColor("#007bff")))
    styles.add(ParagraphStyle(name="NormalBold", fontSize=12, leading=14, spaceAfter=8, fontName="Helvetica-Bold"))


    elements = []

    # ──────────────────────────────────────────────────────────
    # COMPANY LOGO
    # ──────────────────────────────────────────────────────────
    logo_path = os.path.join(settings.STATICFILES_DIRS[0], "logo.png")

    print("LOGO PATH:", logo_path)
    print("EXISTS:", os.path.exists(logo_path))


    if os.path.exists(logo_path):
        elements.append(Image(logo_path, width=120, height=50))
        elements.append(Spacer(1, 12))

    # ──────────────────────────────────────────────────────────
    # TITLE
    # ──────────────────────────────────────────────────────────
    elements.append(Paragraph("INVOICE", styles["InvoiceTitle"]))

    # ──────────────────────────────────────────────────────────
    # INVOICE DETAILS
    # ──────────────────────────────────────────────────────────
    inv_info = f"""
    <b>Invoice No:</b> {invoice.invoice_number}<br/>
    <b>Date:</b> {invoice.created_at.strftime("%d-%m-%Y %H:%M")}<br/>
    <b>Payment Method:</b> {invoice.payment_method.title()}<br/>
    """

    elements.append(Paragraph(inv_info, styles["Normal"]))
    elements.append(Spacer(1, 12))

    # ──────────────────────────────────────────────────────────
    # CUSTOMER DETAILS
    # ──────────────────────────────────────────────────────────
    elements.append(Paragraph("Customer Details", styles["Heading"]))

    customer_info = f"""
    <b>Name:</b> {invoice.customer.name}<br/>
    <b>Phone:</b> {invoice.customer.phone}<br/>
    """

    elements.append(Paragraph(customer_info, styles["Normal"]))
    elements.append(Spacer(1, 18))

    # ──────────────────────────────────────────────────────────
    # ITEMS TABLE
    # ──────────────────────────────────────────────────────────
    elements.append(Paragraph("Order Summary", styles["Heading"]))

    data = [
        ["Item", "Qty", "Price", "Total"]
    ]

    for item in invoice.items.all():
        data.append([
            item.product_name,
            str(item.quantity),
            f"₹ {item.price_at_sale}",
            f"₹ {item.price_at_sale * item.quantity}"
        ])

    table = Table(data, colWidths=[200, 60, 80, 80])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#007bff")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 12),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 20))

    # ──────────────────────────────────────────────────────────
    # TOTALS SUMMARY
    # ──────────────────────────────────────────────────────────
    totals = [
        ["Subtotal", f"₹ {invoice.sub_total}"],
        ["GST", f"₹ {invoice.total_gst}"],
        ["Grand Total", f"₹ {invoice.grand_total}"],
    ]

    totals_table = Table(totals, colWidths=[300, 120])
    totals_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))

    elements.append(totals_table)
    elements.append(Spacer(1, 20))

    # ──────────────────────────────────────────────────────────
    # FOOTER
    # ──────────────────────────────────────────────────────────
    footer = Paragraph(
        "<para alignment='center'><b>Thank you for shopping with us!</b><br/>"
        "For support contact: 12345 67890</para>",
        styles["Normal"]
    )

    elements.append(footer)

    pdf.build(elements)
    return response
