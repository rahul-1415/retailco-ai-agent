import base64
import json
import uuid
import fitz
from openai import OpenAI

from src.extractors.base import BaseExtractor
from src.extractors.pdf_extractor import EXTRACTION_PROMPT
from src.models import Invoice, LineItem

VISION_PROMPT = EXTRACTION_PROMPT.replace(
    "Invoice text:\n",
    "The invoice is provided as an image. Extract all visible text and structure:\n",
)


class VisionExtractor(BaseExtractor):
    def __init__(self, client: OpenAI):
        self.client = client

    def extract(self, pdf_bytes: bytes) -> Invoice:
        images = self._pdf_to_images(pdf_bytes)
        return self._parse_with_vision(images)

    def _pdf_to_images(self, pdf_bytes: bytes) -> list[str]:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        images = []
        for page in doc:
            pix = page.get_pixmap(dpi=150)
            img_bytes = pix.tobytes("png")
            images.append(base64.b64encode(img_bytes).decode("utf-8"))
        return images

    def _parse_with_vision(self, images: list[str]) -> Invoice:
        content = [{"type": "text", "text": VISION_PROMPT}]
        for img_b64 in images:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img_b64}", "detail": "high"},
            })

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": content}],
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
            date=data.get("date", ""),
            line_items=line_items,
            tax_exempt=bool(data.get("tax_exempt", False)),
            tax_exempt_reason=data.get("tax_exempt_reason"),
        )
