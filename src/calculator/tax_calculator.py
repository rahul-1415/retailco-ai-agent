from src.models import Invoice, TaxResult, LineItemTax


class TaxCalculator:
    def calculate(self, invoice: Invoice, classifications: list[dict], extraction_method: str = "pdf") -> TaxResult:
        line_item_taxes = []
        subtotal = 0.0
        total_tax = 0.0

        for item, classification in zip(invoice.line_items, classifications):
            tax_rate = classification["tax_rate"]
            tax_amount = round(item.total_amount * (tax_rate / 100), 2)
            subtotal += item.total_amount
            total_tax += tax_amount
            line_item_taxes.append(LineItemTax(
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_amount=item.total_amount,
                category=classification["category"],
                tax_rate=tax_rate,
                tax_amount=tax_amount,
            ))

        subtotal = round(subtotal, 2)
        total_tax = round(total_tax, 2)

        return TaxResult(
            invoice_id=invoice.invoice_id,
            vendor=invoice.vendor,
            date=invoice.date,
            line_item_taxes=line_item_taxes,
            subtotal=subtotal,
            total_tax=total_tax,
            grand_total=round(subtotal + total_tax, 2),
            tax_exempt=invoice.tax_exempt,
            tax_exempt_reason=invoice.tax_exempt_reason,
            extraction_method=extraction_method,
        )
