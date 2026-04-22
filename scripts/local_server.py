"""
Local dev server — no AWS required.
Serves POST /invoices and GET /invoices/{id} on http://localhost:3001

Usage:
    python scripts/local_server.py

Then set frontend/.env.local:
    NEXT_PUBLIC_API_BASE_URL=http://localhost:3001
"""
import json
import os
import sys
import email
from email.policy import default as email_default
from http.server import BaseHTTPRequestHandler, HTTPServer

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openai import OpenAI
from src.extractors import PDFExtractor, VisionExtractor
from src.classifier import TaxClassifier
from src.calculator import TaxCalculator
from src.agent.tools import TOOLS, SYSTEM_PROMPT

# In-memory store so GET /invoices/{id} works within the same session
_store: dict[str, dict] = {}

_client: OpenAI | None = None
_classifier: TaxClassifier | None = None
_calculator: TaxCalculator | None = None


def _init():
    global _client, _classifier, _calculator
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set in .env")
        sys.exit(1)
    _client = OpenAI(api_key=api_key)
    _classifier = TaxClassifier()
    _calculator = TaxCalculator()
    print("Classifier loaded, OpenAI client ready.")


def _parse_pdf(content_type: str, body_bytes: bytes) -> bytes:
    raw = f"Content-Type: {content_type}\r\n\r\n".encode() + body_bytes
    msg = email.message_from_bytes(raw, policy=email_default)
    for part in msg.iter_parts():
        if part.get_content_type() == "application/pdf" or part.get_filename():
            return part.get_payload(decode=True)
    raise ValueError("No PDF found in request")


def _process(pdf_bytes: bytes) -> dict:
    pdf_extractor = PDFExtractor(_client)
    try:
        invoice = pdf_extractor.extract(pdf_bytes)
        method = "pdf"
    except ValueError:
        vision_extractor = VisionExtractor(_client)
        invoice = vision_extractor.extract(pdf_bytes)
        method = "vision"

    if invoice.tax_exempt:
        classifications = [{"category": "Tax Exempt", "tax_rate": 0.0} for _ in invoice.line_items]
    else:
        categories_text = _classifier.get_categories_text()
        classifications = []
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Available tax categories:\n{categories_text}\n\n"
                    f"Classify each of the following {len(invoice.line_items)} line items:\n"
                    + "\n".join(f"{i+1}. {item.description}" for i, item in enumerate(invoice.line_items))
                ),
            },
        ]
        while len(classifications) < len(invoice.line_items):
            response = _client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=TOOLS,
                tool_choice="required",
                temperature=0,
            )
            message = response.choices[0].message
            messages.append(message)
            if not message.tool_calls:
                break
            tool_results = []
            for tc in message.tool_calls:
                args = json.loads(tc.function.arguments)
                rate = _classifier.get_rate(args["category"])
                classifications.append({"category": args["category"], "tax_rate": rate})
                tool_results.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps({"status": "ok"}),
                })
            messages.extend(tool_results)
            if len(classifications) >= len(invoice.line_items):
                break

    result = _calculator.calculate(invoice, classifications, extraction_method=method)
    return result.to_dict()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"  {self.command} {self.path} → {args[1] if len(args) > 1 else ''}")

    def _send(self, status: int, body: dict):
        payload = json.dumps(body, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(payload)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        if self.path != "/invoices":
            self._send(404, {"error": "Not found"})
            return

        content_type = self.headers.get("Content-Type", "")
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        try:
            pdf_bytes = _parse_pdf(content_type, body)
        except ValueError as e:
            self._send(400, {"error": str(e)})
            return

        print(f"\nProcessing invoice ({len(pdf_bytes):,} bytes)...")
        try:
            result = _process(pdf_bytes)
            invoice_id = result.get("invoice_id", "unknown")
            _store[invoice_id] = result
            print(f"  Done — invoice_id: {invoice_id}, grand_total: {result.get('grand_total')}")
            self._send(200, result)
        except Exception as e:
            print(f"  ERROR: {e}")
            self._send(500, {"error": str(e)})

    def do_GET(self):
        if self.path == "/invoices":
            summaries = [
                {
                    "invoice_id": r["invoice_id"],
                    "vendor": r["vendor"],
                    "date": r.get("date"),
                    "grand_total": r.get("grand_total"),
                    "tax_exempt": r.get("tax_exempt", False),
                    "tax_exempt_reason": r.get("tax_exempt_reason"),
                }
                for r in sorted(_store.values(), key=lambda x: x.get("date", ""), reverse=True)
            ]
            self._send(200, summaries)
        elif self.path.startswith("/invoices/"):
            invoice_id = self.path[len("/invoices/"):]
            result = _store.get(invoice_id)
            if result:
                self._send(200, result)
            else:
                self._send(404, {"error": f"Invoice {invoice_id} not found"})
        else:
            self._send(404, {"error": "Not found"})


if __name__ == "__main__":
    _init()
    port = int(os.environ.get("PORT", 3001))
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"\nLocal server running at http://localhost:{port}")
    print("Set in frontend/.env.local:  NEXT_PUBLIC_API_BASE_URL=http://localhost:3001")
    print("Press Ctrl+C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
