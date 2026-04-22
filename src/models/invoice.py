from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Address:
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None


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
    # Optional metadata
    vendor_address: Optional[Address] = None
    bill_to_name: Optional[str] = None
    bill_to_address: Optional[Address] = None
    customer_id: Optional[str] = None
    due_date: Optional[str] = None
