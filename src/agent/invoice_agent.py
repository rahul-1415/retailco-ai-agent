import json
import boto3
from openai import OpenAI
from decimal import Decimal

from src.models import Invoice, TaxResult
from src.extractors import PDFExtractor, VisionExtractor
from src.classifier import TaxClassifier
from src.calculator import TaxCalculator
from src.agent.tools import TOOLS, SYSTEM_PROMPT


class InvoiceAgent:
    def __init__(self, client: OpenAI, classifier: TaxClassifier, table_name: str, bucket_name: str):
        self.client = client
        self.classifier = classifier
        self.calculator = TaxCalculator()
        self.pdf_extractor = PDFExtractor(client)
        self.vision_extractor = VisionExtractor(client)
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(table_name)
        self.s3 = boto3.client("s3")
        self.bucket_name = bucket_name

    def process(self, pdf_bytes: bytes, s3_key: str) -> TaxResult:
        invoice, extraction_method = self._extract(pdf_bytes)
        self._store_pdf(pdf_bytes, s3_key)

        if invoice.tax_exempt:
            classifications = [{"category": "Tax Exempt", "tax_rate": 0.0} for _ in invoice.line_items]
        else:
            classifications = self._classify(invoice)

        result = self.calculator.calculate(invoice, classifications, extraction_method)
        self._save_result(result)
        return result

    def _extract(self, pdf_bytes: bytes) -> tuple[Invoice, str]:
        try:
            invoice = self.pdf_extractor.extract(pdf_bytes)
            return invoice, "pdf"
        except ValueError:
            invoice = self.vision_extractor.extract(pdf_bytes)
            return invoice, "vision"

    def _classify(self, invoice: Invoice) -> list[dict]:
        categories_text = self.classifier.get_categories_text()
        user_message = (
            f"Available tax categories:\n{categories_text}\n\n"
            f"Classify each of the following {len(invoice.line_items)} line items:\n"
            + "\n".join(f"{i+1}. {item.description}" for i, item in enumerate(invoice.line_items))
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

        classifications = []
        while len(classifications) < len(invoice.line_items):
            response = self.client.chat.completions.create(
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
                classifications.append({
                    "category": args["category"],
                    "tax_rate": self.classifier.get_rate(args["category"]),
                })
                tool_results.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps({"status": "classified", "category": args["category"]}),
                })

            messages.extend(tool_results)

            if len(classifications) >= len(invoice.line_items):
                break

        return classifications

    def _store_pdf(self, pdf_bytes: bytes, s3_key: str) -> None:
        self.s3.put_object(Bucket=self.bucket_name, Key=s3_key, Body=pdf_bytes, ContentType="application/pdf")

    def _save_result(self, result: TaxResult) -> None:
        item = result.to_dict()
        # DynamoDB requires Decimal for floats
        item = json.loads(json.dumps(item), parse_float=Decimal)
        self.table.put_item(Item=item)
