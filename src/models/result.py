from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LineItemTax:
    description: str
    total_amount: float
    category: str
    tax_rate: float
    tax_amount: float
    quantity: Optional[float] = None
    unit_price: Optional[float] = None


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

    def to_dict(self) -> dict:
        return {
            "invoice_id": self.invoice_id,
            "vendor": self.vendor,
            "date": self.date,
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
