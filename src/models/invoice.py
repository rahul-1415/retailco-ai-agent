from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LineItem:
    description: str
    total_amount: float
    quantity: Optional[float] = None
    unit_price: Optional[float] = None


@dataclass
class Invoice:
    invoice_id: str
    vendor: str
    date: str
    line_items: list[LineItem] = field(default_factory=list)
    tax_exempt: bool = False
    tax_exempt_reason: Optional[str] = None
