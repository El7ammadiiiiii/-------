"""
Invoice Service - PDF generation using ReportLab
Creates professional invoices and stores them locally
"""
import os
from datetime import datetime
try:
    from reportlab.lib.pagesizes import A4  # type: ignore[import]
    from reportlab.pdfgen import canvas  # type: ignore[import]
except ImportError as exc:
    raise ImportError(
        "ReportLab is required for PDF generation. Install it via 'pip install reportlab'."
    ) from exc
from typing import Any, Protocol

from database import Order


class _SessionProtocol(Protocol):
    def add(self, instance: Any) -> None: ...

    def commit(self) -> None: ...

    def refresh(self, instance: Any) -> None: ...


async def create_invoice(
    customer_name: str,
    customer_phone: str,
    product_name: str,
    price: float,
    db: _SessionProtocol
) -> str:
    """
    Generate PDF invoice and save to database
    
    Args:
        customer_name: Customer's name
        customer_phone: Customer's WhatsApp number
        product_name: Product/service name
        price: Total amount
        db: Database session
        
    Returns:
        Path to generated PDF file
    """
    # Create invoices directory if not exists
    invoice_dir = "invoices"
    os.makedirs(invoice_dir, exist_ok=True)
    
    # Generate unique filename
    timestamp = int(datetime.now().timestamp())
    filename = f"invoice_{timestamp}.pdf"
    filepath = os.path.join(invoice_dir, filename)
    
    # Create PDF
    c = canvas.Canvas(filepath, pagesize=A4)
    width, height = A4
    
    # Header
    c.setFont("Helvetica-Bold", 24)
    c.drawString(50, height - 50, "Smart Sales Company")
    
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 75, "Professional Services")
    c.drawString(50, height - 90, "Email: info@smartsales.com")
    
    # Invoice title
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, height - 130, "INVOICE / فاتورة")
    
    # Invoice details
    c.setFont("Helvetica", 12)
    current_y = height - 170
    
    c.drawString(50, current_y, f"Invoice Date / التاريخ:")
    c.drawString(250, current_y, datetime.now().strftime("%Y-%m-%d %H:%M"))
    current_y -= 25
    
    c.drawString(50, current_y, f"Invoice Number / الرقم:")
    c.drawString(250, current_y, f"INV-{timestamp}")
    current_y -= 40
    
    # Customer details
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, current_y, "Bill To / العميل:")
    current_y -= 25
    
    c.setFont("Helvetica", 12)
    c.drawString(70, current_y, f"Name / الاسم: {customer_name}")
    current_y -= 20
    c.drawString(70, current_y, f"Phone / الهاتف: {customer_phone}")
    current_y -= 40
    
    # Line separator
    c.line(50, current_y, width - 50, current_y)
    current_y -= 30
    
    # Items header
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, current_y, "Description / الوصف")
    c.drawString(400, current_y, "Amount / المبلغ")
    current_y -= 5
    c.line(50, current_y, width - 50, current_y)
    current_y -= 25
    
    # Item details
    c.setFont("Helvetica", 11)
    c.drawString(50, current_y, product_name)
    c.drawString(400, current_y, f"{price:.2f} KD")
    current_y -= 30
    
    # Line separator
    c.line(50, current_y, width - 50, current_y)
    current_y -= 25
    
    # Total
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, current_y, "Total Amount / المجموع الكلي:")
    c.drawString(400, current_y, f"{price:.2f} KD")
    current_y -= 40
    
    # Payment instructions
    c.setFont("Helvetica", 10)
    c.drawString(50, current_y, "Payment Methods / طرق الدفع:")
    current_y -= 20
    c.drawString(70, current_y, "• Bank Transfer / تحويل بنكي")
    current_y -= 15
    c.drawString(70, current_y, "• Cash / نقداً")
    c.save()
    
    # Save order to database
    new_order = Order(
        customer_phone=customer_phone,
        customer_name=customer_name,
        product_name=product_name,
        total_amount=price,
        invoice_path=filepath,
        status="New"
    )
    
    db.add(new_order)
    db.commit()
    db.refresh(new_order)
    
    print(f"✅ Invoice created: {filepath}")
    
    return filepath


def get_invoice_url(filepath: str) -> str:
    """
    Convert local file path to accessible URL
    In production, upload to cloud storage (S3, Google Drive, etc.)
    For now, returns local path
    """
    # TODO: Upload to cloud storage and return public URL
    # For development, just return the file path
    return filepath
