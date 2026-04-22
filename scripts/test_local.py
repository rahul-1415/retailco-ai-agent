"""
Local test runner — no AWS services required.
Usage:
    python scripts/test_local.py <path-to-pdf>
    python scripts/test_local.py Invoices/RetailCo_Invoice.pdf
"""
import json
import sys
import os

# Load .env before any src imports so OPENAI_API_KEY is available
from dotenv import load_dotenv
load_dotenv()

# Allow imports from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openai import OpenAI
from src.extractors import PDFExtractor, VisionExtractor
from src.classifier import TaxClassifier
from src.calculator import TaxCalculator


def run(pdf_path: str) -> None:
    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        sys.exit(1)

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY not set in .env")
        sys.exit(1)

    client = OpenAI(api_key=api_key)
    classifier = TaxClassifier()
    calculator = TaxCalculator()

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    # --- Extraction ---
    print(f"\nExtracting: {pdf_path}")
    pdf_extractor = PDFExtractor(client)
    try:
        invoice = pdf_extractor.extract(pdf_bytes)
        method = "pdf"
        print("  Method: PDF text + GPT-4o")
    except ValueError:
        print("  PDF text sparse — falling back to Vision")
        vision_extractor = VisionExtractor(client)
        invoice = vision_extractor.extract(pdf_bytes)
        method = "vision"

    print(f"  Invoice ID : {invoice.invoice_id}")
    print(f"  Vendor     : {invoice.vendor}")
    print(f"  Date       : {invoice.date}")
    print(f"  Due Date   : {invoice.due_date}")
    print(f"  Customer ID: {invoice.customer_id}")
    print(f"  Bill To    : {invoice.bill_to_name}")
    print(f"  Tax Exempt : {invoice.tax_exempt} ({invoice.tax_exempt_reason})")
    print(f"  Line Items : {len(invoice.line_items)}")

    # --- Classification ---
    if invoice.tax_exempt:
        print("\nSkipping classification — invoice is tax exempt")
        classifications = [{"category": "Tax Exempt", "tax_rate": 0.0} for _ in invoice.line_items]
    else:
        print("\nClassifying line items...")
        categories_text = classifier.get_categories_text()
        classifications = []

        from src.agent.tools import TOOLS, SYSTEM_PROMPT
        user_message = (
            f"Available tax categories:\n{categories_text}\n\n"
            f"Classify each of the following {len(invoice.line_items)} line items:\n"
            + "\n".join(f"{i+1}. {item.description}" for i, item in enumerate(invoice.line_items))
        )
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

        while len(classifications) < len(invoice.line_items):
            response = client.chat.completions.create(
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
            for tool_call in message.tool_calls:
                args = json.loads(tool_call.function.arguments)
                rate = classifier.get_rate(args["category"])
                classifications.append({"category": args["category"], "tax_rate": rate})
                print(f"  [{len(classifications)}/{len(invoice.line_items)}] {args['description'][:50]:<50} → {args['category']} ({rate}%)")
                tool_results.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps({"status": "ok"}),
                })
            messages.extend(tool_results)

            if len(classifications) >= len(invoice.line_items):
                break

    # --- Calculation ---
    result = calculator.calculate(invoice, classifications, extraction_method=method)

    print(f"\n{'='*60}")
    print(json.dumps(result.to_dict(), indent=2, default=str))
    print(f"\nSubtotal  : ${result.subtotal:,.2f}")
    print(f"Total Tax : ${result.total_tax:,.2f}")
    print(f"Grand Total: ${result.grand_total:,.2f}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_local.py <path-to-pdf>")
        sys.exit(1)
    run(sys.argv[1])
