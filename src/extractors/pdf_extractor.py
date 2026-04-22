import json
import uuid
import fitz
from openai import OpenAI

from src.extractors.base import BaseExtractor
from src.models import Invoice, LineItem, Address

EXTRACTION_PROMPT = """You are extracting structured data from an invoice.

Return ONLY valid JSON with this exact structure:
{
  "invoice_id": "<invoice number or generated uuid if not found>",
  "vendor": "<vendor/company name>",
  "vendor_address": {
    "street": "<street or null>",
    "city": "<city or null>",
    "state": "<state or null>",
    "zip_code": "<zip or null>",
    "phone": "<phone or null>"
  },
  "bill_to_name": "<bill-to name or null>",
  "bill_to_address": {
    "street": "<street or null>",
    "city": "<city or null>",
    "state": "<state or null>",
    "zip_code": "<zip or null>",
    "phone": "<phone or null>"
  },
  "customer_id": "<customer ID or null>",
  "date": "<invoice date as string>",
  "due_date": "<due date as string or null>",
  "tax_exempt": <true or false>,
  "tax_exempt_reason": "<'pre_taxed' | 'used_products' | exact notice text | null>",
  "line_items": [
    {
      "description": "<product description>",
      "quantity": <number or null>,
      "unit_price": <number or null>,
      "total_amount": <number>
    }
  ]
}

Rules:
- tax_exempt detection: scan the ENTIRE invoice text including comments, footers, and notes.
  Set tax_exempt=true and tax_exempt_reason accordingly for:
  * PRE-TAXED (reason="pre_taxed"): "Do not tax, tax has already been applied",
    "Tax included", "All prices include applicable taxes", "VAT included"
  * USED GOODS (reason="used_products"): "Items are non-taxable due to 'Used' status",
    "Used goods — tax exempt", "Secondhand / refurbished — no tax applicable"
  * Unknown notice: set reason to the exact notice text found
- quantity and unit_price: parse from description string if not in separate columns
  (e.g. "Item Name - QTY: 50 $799.50" → quantity=50). Return null if cannot determine.
- total_amount: always required. Strip $, commas, spaces before parsing as float.
- For address fields return null for any sub-field not present in the invoice.
- Do not include any text outside the JSON object.

Invoice text:
"""


class PDFExtractor(BaseExtractor):
    MIN_TEXT_LENGTH = 50

    def __init__(self, client: OpenAI):
        self.client = client

    def extract(self, pdf_bytes: bytes) -> Invoice:
        text = self._extract_text(pdf_bytes)
        if len(text.strip()) < self.MIN_TEXT_LENGTH:
            raise ValueError("insufficient_text")
        return self._parse_with_llm(text)

    def _extract_text(self, pdf_bytes: bytes) -> str:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        return "\n".join(page.get_text() for page in doc)

    def _parse_with_llm(self, text: str) -> Invoice:
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": EXTRACTION_PROMPT + text}],
            response_format={"type": "json_object"},
            temperature=0,
        )
        data = json.loads(response.choices[0].message.content)
        return self._to_invoice(data)

    def _to_invoice(self, data: dict) -> Invoice:
        line_items = [
            LineItem(
                description=item["description"],
                total_amount=float(item["total_amount"]),
                quantity=float(item["quantity"]) if item.get("quantity") is not None else None,
                unit_price=float(item["unit_price"]) if item.get("unit_price") is not None else None,
            )
            for item in data.get("line_items", [])
        ]
        return Invoice(
            invoice_id=data.get("invoice_id") or str(uuid.uuid4()),
            vendor=data.get("vendor", "Unknown"),
            vendor_address=self._to_address(data.get("vendor_address")),
            bill_to_name=data.get("bill_to_name"),
            bill_to_address=self._to_address(data.get("bill_to_address")),
            customer_id=data.get("customer_id"),
            date=data.get("date", ""),
            due_date=data.get("due_date"),
            line_items=line_items,
            tax_exempt=bool(data.get("tax_exempt", False)),
            tax_exempt_reason=data.get("tax_exempt_reason"),
        )

    def _to_address(self, raw: dict | None) -> Address | None:
        if not raw:
            return None
        return Address(
            street=raw.get("street"),
            city=raw.get("city"),
            state=raw.get("state"),
            zip_code=raw.get("zip_code"),
            phone=raw.get("phone"),
        )
