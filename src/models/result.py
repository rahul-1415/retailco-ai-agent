from dataclasses import dataclass, field
from typing import Optional

from src.models.invoice import Address


@dataclass
class LineItemTax:
    description: str
    total_amount: float
    category: str
    tax_rate: float
    tax_amount: float
    quantity: Optional[float] = None
    unit_price: Optional[float] = None


def _address_dict(addr: Optional[Address]) -> Optional[dict]:
    if addr is None:
        return None
    return {
        "street": addr.street,
        "city": addr.city,
        "state": addr.state,
        "zip_code": addr.zip_code,
        "phone": addr.phone,
    }


@dataclass
class TaxResult:
    invoice_id: str
    vendor: str
    date: str
    line_item_taxes: list[LineItemTax] = field(default_factory=list)
    subtotal: float = 0.0
    total_tax: float = 0.0
    grand_total: float = 0.0
    tax_exempt: bool = False
    tax_exempt_reason: Optional[str] = None
    extraction_method: str = "pdf"
    # Optional metadata
    vendor_address: Optional[Address] = None
    bill_to_name: Optional[str] = None
    bill_to_address: Optional[Address] = None
    customer_id: Optional[str] = None
    due_date: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "invoice_id": self.invoice_id,
            "vendor": self.vendor,
            "vendor_address": _address_dict(self.vendor_address),
            "bill_to_name": self.bill_to_name,
            "bill_to_address": _address_dict(self.bill_to_address),
            "customer_id": self.customer_id,
            "date": self.date,
            "due_date": self.due_date,
            "line_item_taxes": [
                {
                    "description": t.description,
                    "quantity": t.quantity,
                    "unit_price": t.unit_price,
                    "total_amount": t.total_amount,
                    "category": t.category,
                    "tax_rate": t.tax_rate,
                    "tax_amount": t.tax_amount,
                }
                for t in self.line_item_taxes
            ],
            "subtotal": self.subtotal,
            "total_tax": self.total_tax,
            "grand_total": self.grand_total,
            "tax_exempt": self.tax_exempt,
            "tax_exempt_reason": self.tax_exempt_reason,
            "extraction_method": self.extraction_method,
        }
