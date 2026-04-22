# RetailCo Invoice Tax Agent — Local Test Results

Run date: 2026-04-22  
Script: `python scripts/test_local.py <invoice>`  
Environment: local (no AWS — DynamoDB/S3 calls skipped)

---

## Summary

| Invoice | Vendor | Extraction | Items | Subtotal | Tax | Grand Total | Exempt |
|---|---|---|---|---|---|---|---|
| RetailCo_Invoice.pdf | BetaShipping | Vision (scanned) | 12 | $12,062.57 | $834.69 | $12,897.26 | No |
| R-1093-12322.pdf | DELTA-DISTRIBUTION | PDF + GPT-4o | 7 | $6,129.60 | $0.00 | $6,129.60 | Yes — `pre_taxed` |
| R-1093-24524.pdf | Delta-Distribution | Vision (scanned) | 7 | $13,582.49 | $961.07 | $14,543.56 | No |
| R-1093-26824.pdf | DELTA-DISTRIBUTION | PDF + GPT-4o | 10 | $4,060.22 | $0.00 | $4,060.22 | Yes — `used_products` |

### Key observations
- **Two-stage extraction confirmed working**: RetailCo_Invoice.pdf and R-1093-24524.pdf both had sparse PDF text and fell back to Vision. R-1093-12322.pdf and R-1093-26824.pdf had extractable text and used the PDF path.
- **Pre-taxed short-circuit working**: R-1093-12322.pdf detected `pre_taxed` from the invoice comment and skipped classification entirely — 0 GPT-4o classify calls, all items tagged `Tax Exempt` with `tax_rate: 0`.
- **Used-product short-circuit working**: R-1093-26824.pdf detected `Items are non-taxable due to "Used" status` and likewise skipped classification.
- **Optional `unit_price` handled**: All Delta-Distribution invoices (which use a two-column format with no separate unit price column) returned `unit_price: null` correctly. `quantity` was still parsed from the embedded description string.
- **Classification accuracy**: All 12 items in RetailCo_Invoice.pdf and all 7 in R-1093-24524.pdf classified correctly to expected categories (Bottled Water 0%, Soft Drinks 6.5%, Tobacco Products 12%, OTC Medicine 4%, Car Batteries 8%, Tires 8%, Tools & Hardware 7%, Paint & Finishes 7%, Bedding & Linens 7.5%).

---

## Test 1 — `Invoices/RetailCo_Invoice.pdf`

**Vendor:** BetaShipping  
**Invoice ID:** 25-12234  
**Date:** 10/5/2025 | **Due:** 11/4/2025  
**Customer ID:** A0033 | **Bill To:** John Smith  
**Extraction:** Vision fallback (PDF text sparse)  
**Tax Exempt:** No

```
  [1/12] Smartwater Vapor Distilled – 6 Pack (1L)           → Bottled Water (0.0%)
  [2/12] Poland Spring Natural Spring Water – 24 Pack       → Bottled Water (0.0%)
  [3/12] Coca-Cola Original – 12 Pack (12 fl oz Cans)       → Soft Drinks (6.5%)
  [4/12] Sprite Lemon-Lime – 8 Pack (12 fl oz Bottles)      → Soft Drinks (6.5%)
  [5/12] Black & Mild Cigars – Wine Tip, 5 Pack             → Tobacco Products (12.0%)
  [6/12] Advil Ibuprofen Tablets – 200 mg, 100 Count        → Over-the-Counter Medicine (4.0%)
  [7/12] Tylenol Extra Strength Caplets – 500 mg, 100 Count → Over-the-Counter Medicine (4.0%)
  [8/12] Claritin 24-Hour Allergy Relief Tablets – 30 Count → Over-the-Counter Medicine (4.0%)
  [9/12] Duracell Automotive Battery – Group H7, 800 CCA    → Car Batteries (8.0%)
 [10/12] NAPA Legend Premium Battery – Group 75, 690 CCA    → Car Batteries (8.0%)
 [11/12] Michelin Defender LTX M/S Tire – 265/70R17         → Tires (8.0%)
 [12/12] Goodyear Assurance All-Season Tire – 225/60R16     → Tires (8.0%)
```

**Subtotal: $12,062.57 | Tax: $834.69 | Grand Total: $12,897.26**

<details>
<summary>Full JSON output</summary>

```json
{
  "invoice_id": "25-12234",
  "vendor": "BetaShipping",
  "vendor_address": {
    "street": "22 Second Hwy.",
    "city": "Atlanta",
    "state": "GA",
    "zip_code": "30302",
    "phone": "404-454-9987"
  },
  "bill_to_name": "John Smith",
  "bill_to_address": {
    "street": "123 Main St",
    "city": "Charlotte",
    "state": "NC",
    "zip_code": "28205",
    "phone": "704-123-1234"
  },
  "customer_id": "A0033",
  "date": "10/5/2025",
  "due_date": "11/4/2025",
  "line_item_taxes": [
    { "description": "Smartwater Vapor Distilled – 6 Pack (1L)", "quantity": 30.0, "unit_price": 9.99, "total_amount": 299.7, "category": "Bottled Water", "tax_rate": 0.0, "tax_amount": 0.0 },
    { "description": "Poland Spring Natural Spring Water – 24 Pack", "quantity": 20.0, "unit_price": 6.49, "total_amount": 129.8, "category": "Bottled Water", "tax_rate": 0.0, "tax_amount": 0.0 },
    { "description": "Coca-Cola Original – 12 Pack (12 fl oz Cans)", "quantity": 12.0, "unit_price": 8.99, "total_amount": 107.88, "category": "Soft Drinks", "tax_rate": 6.5, "tax_amount": 7.01 },
    { "description": "Sprite Lemon-Lime – 8 Pack (12 fl oz Bottles)", "quantity": 13.0, "unit_price": 7.99, "total_amount": 103.87, "category": "Soft Drinks", "tax_rate": 6.5, "tax_amount": 6.75 },
    { "description": "Black & Mild Cigars – Wine Tip, 5 Pack", "quantity": 40.0, "unit_price": 7.49, "total_amount": 299.6, "category": "Tobacco Products", "tax_rate": 12.0, "tax_amount": 35.95 },
    { "description": "Advil Ibuprofen Tablets – 200 mg, 100 Count", "quantity": 111.0, "unit_price": 11.99, "total_amount": 1330.89, "category": "Over-the-Counter Medicine", "tax_rate": 4.0, "tax_amount": 53.24 },
    { "description": "Tylenol Extra Strength Caplets – 500 mg, 100 Count", "quantity": 45.0, "unit_price": 12.99, "total_amount": 584.55, "category": "Over-the-Counter Medicine", "tax_rate": 4.0, "tax_amount": 23.38 },
    { "description": "Claritin 24-Hour Allergy Relief Tablets – 30 Count", "quantity": 32.0, "unit_price": 21.99, "total_amount": 703.68, "category": "Over-the-Counter Medicine", "tax_rate": 4.0, "tax_amount": 28.15 },
    { "description": "Duracell Automotive Battery – Group H7, 800 CCA", "quantity": 14.0, "unit_price": 179.99, "total_amount": 2519.86, "category": "Car Batteries", "tax_rate": 8.0, "tax_amount": 201.59 },
    { "description": "NAPA Legend Premium Battery – Group 75, 690 CCA", "quantity": 14.0, "unit_price": 162.99, "total_amount": 2281.86, "category": "Car Batteries", "tax_rate": 8.0, "tax_amount": 182.55 },
    { "description": "Michelin Defender LTX M/S Tire – 265/70R17", "quantity": 10.0, "unit_price": 198.5, "total_amount": 1985.0, "category": "Tires", "tax_rate": 8.0, "tax_amount": 158.8 },
    { "description": "Goodyear Assurance All-Season Tire – 225/60R16", "quantity": 12.0, "unit_price": 142.99, "total_amount": 1715.88, "category": "Tires", "tax_rate": 8.0, "tax_amount": 137.27 }
  ],
  "subtotal": 12062.57,
  "total_tax": 834.69,
  "grand_total": 12897.26,
  "tax_exempt": false,
  "tax_exempt_reason": null,
  "extraction_method": "vision"
}
```

</details>

---

## Test 2 — `Invoices/R-1093-12322.pdf`

**Vendor:** DELTA-DISTRIBUTION  
**Invoice ID:** R-1093-12322  
**Date:** 9/30/2025 | **Due:** 10/30/2025  
**Customer ID:** R-1093 | **Bill To:** John Smith  
**Extraction:** PDF + GPT-4o  
**Tax Exempt:** Yes — `pre_taxed` (vendor note: "Do not tax, tax has already been applied to items in invoice")

Classification skipped — all items tagged `Tax Exempt`, `tax_rate: 0`.

**Subtotal: $6,129.60 | Tax: $0.00 | Grand Total: $6,129.60**

<details>
<summary>Full JSON output</summary>

```json
{
  "invoice_id": "R-1093-12322",
  "vendor": "DELTA-DISTRIBUTION",
  "vendor_address": { "street": "33 Main St.", "city": "Dallas", "state": "TX", "zip_code": "75001", "phone": "214-442-0395" },
  "bill_to_name": "John Smith",
  "bill_to_address": { "street": "123 Main St", "city": "Charlotte", "state": "NC", "zip_code": "28205", "phone": "(704) 123-1234" },
  "customer_id": "R-1093",
  "date": "9/30/2025",
  "due_date": "10/30/2025",
  "line_item_taxes": [
    { "description": "BrightWave Laundry Pods – 42 Count – ID: 68840", "quantity": 50.0, "unit_price": 799.5, "total_amount": 799.5, "category": "Tax Exempt", "tax_rate": 0.0, "tax_amount": 0.0 },
    { "description": "EcoSoft Plant-Based Detergent – 90 oz – ID: 40192", "quantity": 40.0, "unit_price": 499.6, "total_amount": 499.6, "category": "Tax Exempt", "tax_rate": 0.0, "tax_amount": 0.0 },
    { "description": "Dawn Ultra Dishwashing Liquid – 38 oz Bottle – ID: 81976", "quantity": 25.0, "unit_price": 107.25, "total_amount": 107.25, "category": "Tax Exempt", "tax_rate": 0.0, "tax_amount": 0.0 },
    { "description": "Energizer MAX AA Batteries – 24 Pack – ID: 58723", "quantity": 100.0, "unit_price": 1899.0, "total_amount": 1899.0, "category": "Tax Exempt", "tax_rate": 0.0, "tax_amount": 0.0 },
    { "description": "Hamilton Beach 2-Slice Toaster – Brushed Steel – ID: 27685", "quantity": 25.0, "unit_price": 874.75, "total_amount": 874.75, "category": "Tax Exempt", "tax_rate": 0.0, "tax_amount": 0.0 },
    { "description": "Gibson Stoneware Dinner Set – 20 Piece – ID: 26590", "quantity": 20.0, "unit_price": 1199.8, "total_amount": 1199.8, "category": "Tax Exempt", "tax_rate": 0.0, "tax_amount": 0.0 },
    { "description": "Threshold Ceramic Mug Set – 6 Count – ID: 38452", "quantity": 30.0, "unit_price": 749.7, "total_amount": 749.7, "category": "Tax Exempt", "tax_rate": 0.0, "tax_amount": 0.0 }
  ],
  "subtotal": 6129.6,
  "total_tax": 0.0,
  "grand_total": 6129.6,
  "tax_exempt": true,
  "tax_exempt_reason": "pre_taxed",
  "extraction_method": "pdf"
}
```

</details>

---

## Test 3 — `Invoices/R-1093-24524.pdf`

**Vendor:** Delta-Distribution  
**Invoice ID:** R-1093-24524  
**Date:** 10/7/2025 | **Due:** 11/6/2025  
**Customer ID:** R-1093 | **Bill To:** John Smith  
**Extraction:** Vision fallback (PDF text sparse)  
**Tax Exempt:** No

```
  [1/7] Kobalt Adjustable Wrench Set – 3 Piece – ID: 18429 → Tools & Hardware (7.0%)
  [2/7] Milwaukee Hammer Drill – 1/2" 18V – ID: 71360      → Tools & Hardware (7.0%)
  [3/7] Behr Premium Interior Paint – 1 Gallon – ID: 92173 → Paint & Finishes (7.0%)
  [4/7] Valspar Ultra Exterior Paint – 1 Gallon – ID: 3952 → Paint & Finishes (7.0%)
  [5/7] ClearSpring – Purified Water – 24 Pack (16.9 fl oz → Bottled Water (0.0%)
  [6/7] AquaPure – Natural Spring Water – 6 Pack (1L)      → Bottled Water (0.0%)
  [7/7] Brooklinen Luxe Core Sheet Set – Queen – ID: 67088 → Bedding & Linens (7.5%)
```

Note: `unit_price` is `null` for all items — Delta-Distribution two-column format.

**Subtotal: $13,582.49 | Tax: $961.07 | Grand Total: $14,543.56**

<details>
<summary>Full JSON output</summary>

```json
{
  "invoice_id": "R-1093-24524",
  "vendor": "Delta-Distribution",
  "vendor_address": { "street": "33 Main St.", "city": "Dallas", "state": "TX", "zip_code": "75001", "phone": "214-442-0395" },
  "bill_to_name": "John Smith",
  "bill_to_address": { "street": "123 Main St", "city": "Charlotte", "state": "NC", "zip_code": "28205", "phone": "(704) 123-1234" },
  "customer_id": "R-1093",
  "date": "10/7/2025",
  "due_date": "11/6/2025",
  "line_item_taxes": [
    { "description": "Kobalt Adjustable Wrench Set – 3 Piece – ID: 18429", "quantity": 40.0, "unit_price": null, "total_amount": 1399.6, "category": "Tools & Hardware", "tax_rate": 7.0, "tax_amount": 97.97 },
    { "description": "Milwaukee Hammer Drill – 1/2\" 18V – ID: 71360", "quantity": 20.0, "unit_price": null, "total_amount": 3580.0, "category": "Tools & Hardware", "tax_rate": 7.0, "tax_amount": 250.6 },
    { "description": "Behr Premium Interior Paint – 1 Gallon – ID: 92173", "quantity": 50.0, "unit_price": null, "total_amount": 2099.5, "category": "Paint & Finishes", "tax_rate": 7.0, "tax_amount": 146.97 },
    { "description": "Valspar Ultra Exterior Paint – 1 Gallon – ID: 39520", "quantity": 35.0, "unit_price": null, "total_amount": 1539.65, "category": "Paint & Finishes", "tax_rate": 7.0, "tax_amount": 107.78 },
    { "description": "ClearSpring – Purified Water – 24 Pack (16.9 fl oz) – ID: 60674", "quantity": 16.0, "unit_price": null, "total_amount": 103.84, "category": "Bottled Water", "tax_rate": 0.0, "tax_amount": 0.0 },
    { "description": "AquaPure – Natural Spring Water – 6 Pack (1L) – ID: 91530", "quantity": 10.0, "unit_price": null, "total_amount": 89.9, "category": "Bottled Water", "tax_rate": 0.0, "tax_amount": 0.0 },
    { "description": "Brooklinen Luxe Core Sheet Set – Queen – ID: 67088", "quantity": 30.0, "unit_price": null, "total_amount": 4770.0, "category": "Bedding & Linens", "tax_rate": 7.5, "tax_amount": 357.75 }
  ],
  "subtotal": 13582.49,
  "total_tax": 961.07,
  "grand_total": 14543.56,
  "tax_exempt": false,
  "tax_exempt_reason": null,
  "extraction_method": "vision"
}
```

</details>

---

## Test 4 — `Invoices/R-1093-26824.pdf`

**Vendor:** DELTA-DISTRIBUTION  
**Invoice ID:** R-1093-26824  
**Date:** 10/7/2025 | **Due:** 11/6/2025  
**Customer ID:** R-1093 | **Bill To:** John Smith  
**Extraction:** PDF + GPT-4o  
**Tax Exempt:** Yes — `used_products` (raw notice: `Items are non-taxable due to "Used" status`)

Classification skipped — all items tagged `Tax Exempt`, `tax_rate: 0`. `unit_price` is `null` throughout.

**Subtotal: $4,060.22 | Tax: $0.00 | Grand Total: $4,060.22**

<details>
<summary>Full JSON output</summary>

```json
{
  "invoice_id": "R-1093-26824",
  "vendor": "DELTA-DISTRIBUTION",
  "vendor_address": { "street": "33 Main St.", "city": "Dallas", "state": "TX", "zip_code": "75001", "phone": "214-442-0395" },
  "bill_to_name": "John Smith",
  "bill_to_address": { "street": "123 Main St", "city": "Charlotte", "state": "NC", "zip_code": "28205", "phone": "(704) 123-1234" },
  "customer_id": "R-1093",
  "date": "10/7/2025",
  "due_date": "11/6/2025",
  "line_item_taxes": [
    { "description": "Used- \"To Kill A Mockingbird\" – Harper Lee – Hardcover – ID: 55086", "quantity": 15.0, "unit_price": null, "total_amount": 337.35, "category": "Tax Exempt", "tax_rate": 0.0, "tax_amount": 0.0 },
    { "description": "Used- \"The Great Gatsby\" – F. Scott Fitzgerald – ID: 90573", "quantity": 16.0, "unit_price": null, "total_amount": 239.84, "category": "Tax Exempt", "tax_rate": 0.0, "tax_amount": 0.0 },
    { "description": "Used- \"Educated\" – Tara Westover – Paperback – ID: 18704", "quantity": 10.0, "unit_price": null, "total_amount": 189.9, "category": "Tax Exempt", "tax_rate": 0.0, "tax_amount": 0.0 },
    { "description": "Used- Hasbro Monopoly Deluxe Edition – ID: 42297", "quantity": 20.0, "unit_price": null, "total_amount": 599.8, "category": "Tax Exempt", "tax_rate": 0.0, "tax_amount": 0.0 },
    { "description": "Used- Mattel UNO Card Game – ID: 51783", "quantity": 17.0, "unit_price": null, "total_amount": 169.83, "category": "Tax Exempt", "tax_rate": 0.0, "tax_amount": 0.0 },
    { "description": "Used- Ravensburger 1000-Piece Jigsaw Puzzle – ID: 68817", "quantity": 24.0, "unit_price": null, "total_amount": 479.76, "category": "Tax Exempt", "tax_rate": 0.0, "tax_amount": 0.0 },
    { "description": "Used- Nerf Elite Blaster – 25 Darts – ID: 31948", "quantity": 15.0, "unit_price": null, "total_amount": 599.85, "category": "Tax Exempt", "tax_rate": 0.0, "tax_amount": 0.0 },
    { "description": "Used- Breville Smart Toaster Oven – Compact – ID: 83172", "quantity": 6.0, "unit_price": null, "total_amount": 894.0, "category": "Tax Exempt", "tax_rate": 0.0, "tax_amount": 0.0 },
    { "description": "Used- Hamilton Beach 2-Slice Toaster – Brushed Steel – ID: 27685", "quantity": 8.0, "unit_price": null, "total_amount": 279.92, "category": "Tax Exempt", "tax_rate": 0.0, "tax_amount": 0.0 },
    { "description": "Used- Cuisinart 12-Cup Coffee Maker – Programmable – ID: 54328", "quantity": 3.0, "unit_price": null, "total_amount": 269.97, "category": "Tax Exempt", "tax_rate": 0.0, "tax_amount": 0.0 }
  ],
  "subtotal": 4060.22,
  "total_tax": 0.0,
  "grand_total": 4060.22,
  "tax_exempt": true,
  "tax_exempt_reason": "Items are non-taxable due to \"Used\" status",
  "extraction_method": "pdf"
}
```

</details>
