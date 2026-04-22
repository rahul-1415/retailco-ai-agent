import json
import os
import uuid
import email
from email.policy import default as email_default
from decimal import Decimal

import boto3
from openai import OpenAI

from src.config import get_openai_key
from src.classifier import TaxClassifier
from src.agent import InvoiceAgent

# Initialised once at cold start
_agent: InvoiceAgent | None = None
_classifier: TaxClassifier | None = None


def _get_agent() -> InvoiceAgent:
    global _agent, _classifier
    if _agent is None:
        client = OpenAI(api_key=get_openai_key())
        _classifier = TaxClassifier()
        _agent = InvoiceAgent(
            client=client,
            classifier=_classifier,
            table_name=os.environ["DYNAMODB_TABLE"],
            bucket_name=os.environ["INVOICES_BUCKET"],
        )
    return _agent


def _response(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, default=str),
    }


def _parse_pdf_from_multipart(event: dict) -> bytes:
    content_type = event.get("headers", {}).get("content-type") or event.get("headers", {}).get("Content-Type", "")
    body = event.get("body", "")

    if event.get("isBase64Encoded"):
        import base64
        body_bytes = base64.b64decode(body)
    else:
        body_bytes = body.encode("utf-8") if isinstance(body, str) else body

    raw = f"Content-Type: {content_type}\r\n\r\n".encode() + body_bytes
    msg = email.message_from_bytes(raw, policy=email_default)

    for part in msg.iter_parts():
        if part.get_content_type() == "application/pdf" or part.get_filename():
            return part.get_payload(decode=True)

    raise ValueError("No PDF file found in multipart request")


def _handle_post(event: dict) -> dict:
    try:
        pdf_bytes = _parse_pdf_from_multipart(event)
    except ValueError as e:
        return _response(400, {"error": str(e)})

    s3_key = f"invoices/{uuid.uuid4()}.pdf"
    try:
        agent = _get_agent()
        result = agent.process(pdf_bytes, s3_key)
        return _response(200, result.to_dict())
    except Exception as e:
        return _response(500, {"error": str(e)})


def _decimal_to_python(o):
    if isinstance(o, Decimal):
        return float(o)
    return str(o)


def _handle_list() -> dict:
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(os.environ["DYNAMODB_TABLE"])
    response = table.scan(
        ProjectionExpression="invoice_id, vendor, #d, grand_total, tax_exempt, tax_exempt_reason",
        ExpressionAttributeNames={"#d": "date"},
    )
    items = json.loads(json.dumps(response.get("Items", []), default=_decimal_to_python))
    items.sort(key=lambda x: x.get("date", ""), reverse=True)
    return _response(200, items)


def _handle_get(event: dict) -> dict:
    invoice_id = event.get("pathParameters", {}).get("invoice_id")
    if not invoice_id:
        return _response(400, {"error": "invoice_id path parameter is required"})

    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(os.environ["DYNAMODB_TABLE"])
    response = table.get_item(Key={"invoice_id": invoice_id})
    item = response.get("Item")

    if not item:
        return _response(404, {"error": f"Invoice {invoice_id} not found"})

    item = json.loads(json.dumps(item, default=_decimal_to_python))
    return _response(200, item)


def handler(event: dict, context) -> dict:
    method = event.get("httpMethod", "")
    resource = event.get("resource", "")

    if method == "POST" and resource == "/invoices":
        return _handle_post(event)
    if method == "GET" and resource == "/invoices":
        return _handle_list()
    if method == "GET" and resource == "/invoices/{invoice_id}":
        return _handle_get(event)

    return _response(404, {"error": "Not found"})
