import pytest
from src.models.invoice import Invoice, LineItem
from src.calculator.tax_calculator import TaxCalculator


@pytest.fixture
def calculator():
    return TaxCalculator()


def _invoice(line_items):
    return Invoice(invoice_id="TEST-001", vendor="Test Vendor", date="2024-01-01", line_items=line_items)


def test_single_line_item(calculator):
    invoice = _invoice([LineItem(description="Widget", total_amount=100.0)])
    result = calculator.calculate(invoice, [{"category": "Electronics", "tax_rate": 8.0}])

    assert result.subtotal == 100.0
    assert result.total_tax == 8.0
    assert result.grand_total == 108.0
    assert len(result.line_item_taxes) == 1
    assert result.line_item_taxes[0].category == "Electronics"
    assert result.line_item_taxes[0].tax_rate == 8.0
    assert result.line_item_taxes[0].tax_amount == 8.0


def test_multiple_line_items(calculator):
    invoice = _invoice([
        LineItem(description="Item A", total_amount=200.0),
        LineItem(description="Item B", total_amount=50.0),
    ])
    classifications = [
        {"category": "Electronics", "tax_rate": 10.0},
        {"category": "Clothing", "tax_rate": 0.0},
    ]
    result = calculator.calculate(invoice, classifications)

    assert result.subtotal == 250.0
    assert result.total_tax == 20.0
    assert result.grand_total == 270.0


def test_zero_tax_rate(calculator):
    invoice = _invoice([LineItem(description="Exempt Item", total_amount=500.0)])
    result = calculator.calculate(invoice, [{"category": "Grocery - Food Items", "tax_rate": 0.0}])

    assert result.total_tax == 0.0
    assert result.grand_total == 500.0


def test_tax_exempt_invoice(calculator):
    invoice = _invoice([LineItem(description="Goods", total_amount=1000.0)])
    invoice.tax_exempt = True
    invoice.tax_exempt_reason = "pre_taxed"
    result = calculator.calculate(invoice, [{"category": "Electronics", "tax_rate": 0.0}])

    assert result.tax_exempt is True
    assert result.tax_exempt_reason == "pre_taxed"
    assert result.total_tax == 0.0


def test_rounding(calculator):
    invoice = _invoice([LineItem(description="Item", total_amount=33.33)])
    result = calculator.calculate(invoice, [{"category": "Electronics", "tax_rate": 7.5}])

    assert result.total_tax == round(33.33 * 0.075, 2)
    assert result.grand_total == round(33.33 + result.total_tax, 2)


def test_result_metadata(calculator):
    invoice = _invoice([LineItem(description="Item", total_amount=100.0)])
    result = calculator.calculate(invoice, [{"category": "Electronics", "tax_rate": 5.0}], extraction_method="vision")

    assert result.invoice_id == "TEST-001"
    assert result.vendor == "Test Vendor"
    assert result.extraction_method == "vision"
