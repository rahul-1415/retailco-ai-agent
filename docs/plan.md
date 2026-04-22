# RetailCo Invoice Tax Agent — Implementation Plan

## Context
RetailCo receives invoices from hundreds of vendors in varying formats (native PDF, scanned PDFs, structured/unstructured). The Accounts Payable team manually assigns tax categories per line item — this agent automates that. The system must extract line items, classify each to one of 50 tax categories, calculate tax, and produce a structured result. Deployed on AWS Free Tier via CloudFormation.

---

## Architecture

```
                        ┌──────────────────────────────────────────────┐
                        │                AWS (Free Tier)                │
                        │                                               │
  POST /invoices        │  API Gateway       Lambda Function            │
  (multipart PDF) ─────►│  (REST API)  ─────► (invoice_processor)      │
                        │                          │                    │
  GET /invoices/{id}    │                    ┌─────┼─────────────────┐  │
  (fetch result) ──────►│                    │     │                 │  │
                        │                    ▼     ▼                 │  │
                        │              SSM Param   S3 (store PDF)   │  │
                        │              (OpenAI Key)                  │  │
                        │                    └─────┼─────────────────┘  │
                        │                          ▼                    │
                        │                    OpenAI Agent               │
                        │                    (GPT-4o)                   │
                        │                     │      │                  │
                        │             Extract  │      │ Classify         │
                        │             Tool     │      │ Tool             │
                        │                     ▼      ▼                  │
                        │               Line Items + Tax Categories      │
                        │                          │                    │
                        │                          ▼                    │
                        │                   DynamoDB Table              │
                        │                   (tax_results)               │
                        │                          │                    │
                        │                          ▼                    │
                        │              Returns TaxResult JSON           │
                        │              directly in HTTP response        │
                        └──────────────────────────────────────────────┘
```

**Trigger:** `POST /invoices` via API Gateway → Lambda (synchronous, result returned in response)
**LLM:** OpenAI GPT-4o (vision-capable, handles both native text and scanned PDFs)
**Key Storage:** SSM Parameter Store (SecureString) — fetched by Lambda at runtime
**Storage:** DynamoDB for queryable results + S3 for raw PDF storage
**IaC:** Single CloudFormation YAML (`infrastructure/template.yaml`)

### API Endpoints
| Method | Path | Description |
|---|---|---|
| `POST` | `/invoices` | Upload PDF (multipart/form-data), returns full TaxResult JSON |
| `GET` | `/invoices/{invoice_id}` | Retrieve a previously processed result from DynamoDB |

---

## Project Structure

```
retailco-ai-agent/
├── src/
│   ├── models/
│   │   ├── __init__.py
│   │   ├── invoice.py          # LineItem, Invoice dataclasses
│   │   └── result.py           # TaxResult, LineItemTax dataclasses
│   ├── extractors/
│   │   ├── __init__.py
│   │   ├── base.py             # Abstract BaseExtractor
│   │   ├── pdf_extractor.py    # PyMuPDF for native-text PDFs
│   │   └── vision_extractor.py # OpenAI Vision for scanned/image PDFs
│   ├── classifier/
│   │   ├── __init__.py
│   │   └── tax_classifier.py   # Loads CSV, matches description → category
│   ├── calculator/
│   │   ├── __init__.py
│   │   └── tax_calculator.py   # Applies tax rate to line item amounts
│   └── agent/
│       ├── __init__.py
│       ├── tools.py            # OpenAI tool definitions (extract, classify, calculate, save)
│       └── invoice_agent.py    # Agent loop orchestrator
├── lambda_handler.py           # AWS Lambda entry point
├── infrastructure/
│   └── template.yaml           # CloudFormation (S3, Lambda, DynamoDB, SSM, API Gateway, IAM)
├── frontend/
│   ├── app/
│   │   ├── layout.tsx          # Root layout + metadata
│   │   ├── page.tsx            # State machine: upload → processing → results/error
│   │   └── globals.css
│   ├── components/
│   │   ├── Header.tsx          # Nav + invoice ID lookup
│   │   ├── UploadPanel.tsx     # Drag-drop + file card + process button
│   │   ├── ProcessingPanel.tsx # Spinner + rotating step labels
│   │   ├── ErrorPanel.tsx      # Error card + retry
│   │   └── results/
│   │       ├── ResultsPanel.tsx    # Top bar, badges, composes sub-components
│   │       ├── MetadataCards.tsx   # 8-cell metadata grid
│   │       ├── LineItemsTable.tsx  # Line items with category pills
│   │       └── TotalsCard.tsx      # Subtotal / tax / grand total
│   ├── lib/
│   │   ├── types.ts            # TaxResult, LineItemTax, Address interfaces
│   │   ├── api.ts              # processInvoice(), lookupInvoice()
│   │   └── format.ts           # fmt(), fmtAddress(), TAX_EXEMPT_LABELS
│   ├── next.config.js
│   ├── tailwind.config.ts
│   └── package.json
├── docs/
│   ├── plan.md                 # This file — current implementation plan
│   ├── plan-history.md         # Chronological record of all planning changes
│   └── design-decisions.md     # All technical and product design decisions
├── scripts/
│   └── test_local.py           # Local pipeline test without AWS
├── tax_rate_by_category.csv
├── Invoices/                   # Sample invoices
├── requirements.txt
├── requirements-dev.txt
├── .env
└── .gitignore
```

---

## Implementation Steps

### 1. Models (`src/models/`)
- `LineItem`: `description`, `quantity: Optional[float]`, `unit_price: Optional[float]`, `total_amount: float`
  - `quantity` and `unit_price` are `Optional` — some invoices (e.g. Delta-Distribution) embed them inside the description string rather than separate columns; GPT-4o parses them out where possible, leaves `None` where not present
- `Invoice`: `invoice_id`, `vendor`, `date`, `line_items: list[LineItem]`, `tax_exempt: bool`, `tax_exempt_reason: Optional[str]`
  - `tax_exempt: bool` — set when any tax exemption notice is detected anywhere in the invoice (comments, headers, footers, line-level notes)
  - `tax_exempt_reason: Optional[str]` — preserves the exact reason found: `"pre_taxed"` (tax already applied) or `"used_products"` (non-taxable secondhand/used goods), or the raw notice text if it doesn't match a known pattern
- `LineItemTax`: `line_item`, `category`, `tax_rate`, `tax_amount`
- `TaxResult`: `invoice_id`, `line_item_taxes`, `subtotal`, `total_tax`, `grand_total`, `tax_exempt: bool`, `tax_exempt_reason: Optional[str]`, `extraction_method: str`

### 2. Extractors (`src/extractors/`)
- `BaseExtractor`: abstract `extract(pdf_bytes) -> Invoice`
- `PDFExtractor`: uses **PyMuPDF** (`fitz`) to extract text from native PDFs, passes raw text to GPT-4o for structured parsing into `Invoice`
- `VisionExtractor`: sends PDF page as base64 image to OpenAI GPT-4o vision; structured JSON response parsed into `Invoice`
- Auto-detection: try `PDFExtractor` first (fast, free); fall back to `VisionExtractor` if extracted text is sparse (< 50 meaningful characters)

**GPT-4o extraction prompt handles all structural variations:**
- Varying column orders (Qty | Price | Desc vs Desc | Qty | Price)
- Quantity/ID/price embedded in description strings (e.g. `"BrightWave Laundry Pods – ID: 68840 - QTY: 50 $799.50"`) — GPT-4o reads the full line and fills `quantity`, `unit_price`, `total_amount` intelligently; if quantity/unit_price cannot be determined, returns `null` for those fields
- Missing or inconsistent `$` signs in amount fields — parsed as float after context-aware cleaning

### 3. Classifier (`src/classifier/tax_classifier.py`)
- Loads `tax_rate_by_category.csv` into memory on cold start
- Exposed as an **OpenAI tool**: `classify_line_item(description: str) -> {category, tax_rate}`
- Uses GPT-4o to semantically match description to the closest of the 50 categories
- If `Invoice.pre_taxed` is `True`, classifier skips GPT-4o call entirely and returns `{category: "Pre-Taxed", tax_rate: 0}` for every line item

### 4. Calculator (`src/calculator/tax_calculator.py`)
- Pure function: `calculate_tax(amount: float, tax_rate: float) -> float`
- Aggregates line-level taxes into `TaxResult`

### 5. Agent (`src/agent/`)

**Tools registered with OpenAI:**
```python
tools = [
    extract_invoice_data,    # returns structured Invoice JSON
    classify_line_item,      # returns {category, tax_rate} for a description
    calculate_line_tax,      # returns tax_amount for a line
    save_result,             # writes TaxResult to DynamoDB
]
```

**Agent system prompt includes these explicit rules:**

```
Tax exemption detection — scan the ENTIRE invoice (comments, notes, headers,
footers, line-level annotations) for any language indicating items should not
be taxed. There are two distinct exemption types to recognise:

  1. PRE-TAXED — tax was already applied by the vendor before invoicing:
     - "Do not tax, tax has already been applied to items in invoice"
     - "Tax included", "All prices include applicable taxes"
     - "VAT included", "Tax already calculated"
     → set tax_exempt=true, tax_exempt_reason="pre_taxed"

  2. USED / NON-TAXABLE GOODS — items are exempt because they are secondhand
     or used products, which are not subject to sales tax:
     - "Items are non-taxable due to 'Used' status"
     - "Used goods — tax exempt"
     - "Secondhand / refurbished — no tax applicable"
     → set tax_exempt=true, tax_exempt_reason="used_products"

  If a notice is found but does not clearly match either type, set
  tax_exempt=true and tax_exempt_reason=<exact text of the notice>.

  If tax_exempt=true for ANY reason, set tax_rate=0 and tax_amount=0 for ALL
  line items. Do not call classify_line_item. Record the reason in the result.

Embedded field parsing — some invoices do not use separate quantity/price columns.
Parse quantity, unit_price, and total_amount from the description string when
column-based values are absent. Return null for fields that genuinely cannot be
determined from any part of the invoice text.

Amount formatting — strip non-numeric characters ($, commas, spaces) before
parsing monetary values as floats. Do not assume a $ prefix is always present.
```

**Agent loop (`invoice_agent.py`):**
1. Receive PDF bytes
2. Call `extract_invoice_data` tool — returns `Invoice` with `tax_exempt` and `tax_exempt_reason` set
3. If `tax_exempt=True`: skip to step 6 with all tax values as 0, carry reason through to result
4. For each line item, call `classify_line_item`
5. Call `calculate_line_tax` for each
6. Call `save_result` with final `TaxResult`
7. Return `TaxResult` to caller

### 6. Lambda Handler (`lambda_handler.py`)
- Entry: `handler(event, context)`
- On cold start: fetch OpenAI API key from SSM Parameter Store (`/retailco/openai-api-key`), cache in module scope
- Routes on `event['httpMethod']`:
  - `POST /invoices` → parse multipart body, extract PDF bytes, upload to S3, run `InvoiceAgent`, return TaxResult JSON
  - `GET /invoices/{invoice_id}` → read from DynamoDB, return stored result
- Returns API Gateway-compatible response (`statusCode`, `headers`, `body`)

### 7. SSM Parameter Store
- Parameter name: `/retailco/openai-api-key`
- Type: `SecureString` (encrypted at rest with AWS KMS default key — free)
- Set manually once before deployment: `aws ssm put-parameter --name /retailco/openai-api-key --value <key> --type SecureString`
- Lambda IAM role granted `ssm:GetParameter` on this specific ARN only
- Lambda caches the value in module scope — fetched once per cold start, not per invocation

### 8. CloudFormation (`infrastructure/template.yaml`)
Resources:
| Resource | Type | Notes |
|---|---|---|
| `InvoicesBucket` | `AWS::S3::Bucket` | Stores uploaded PDFs |
| `TaxResultsTable` | `AWS::DynamoDB::Table` | PK: `invoice_id`, free tier |
| `InvoiceProcessorFunction` | `AWS::Lambda::Function` | Python 3.12, 512MB, 29s timeout; SSM param name passed as env var |
| `LambdaExecutionRole` | `AWS::IAM::Role` | S3 write + DynamoDB read/write + SSM GetParameter |
| `InvoiceApi` | `AWS::ApiGateway::RestApi` | REST API with binary media type support |
| `InvoicesResource` | `AWS::ApiGateway::Resource` | `/invoices` path |
| `InvoiceIdResource` | `AWS::ApiGateway::Resource` | `/invoices/{invoice_id}` path |
| `PostMethod` | `AWS::ApiGateway::Method` | `POST /invoices` → Lambda proxy |
| `GetMethod` | `AWS::ApiGateway::Method` | `GET /invoices/{invoice_id}` → Lambda proxy |
| `ApiDeployment` | `AWS::ApiGateway::Deployment` | Deploys to `prod` stage |
| `LambdaApiPermission` | `AWS::Lambda::Permission` | Allow API Gateway to invoke Lambda |
| `ErrorMetricFilter` | `AWS::Logs::MetricFilter` | Scans Lambda logs for `ERROR`, emits `InvoiceProcessingErrors` metric |
| `ErrorAlarm` | `AWS::CloudWatch::Alarm` | Triggers when `InvoiceProcessingErrors >= 1` in 5 min window |
| `AlarmTopic` | `AWS::SNS::Topic` | Receives alarm notifications; add email subscription post-deploy |

No `OpenAIApiKey` CloudFormation parameter — key lives in SSM, never touches CloudFormation.

### 9. Frontend (`frontend/`)
- **Framework:** Next.js 14, TypeScript, Tailwind CSS
- **Run:** `cd frontend && npm install && npm run dev` → `http://localhost:3000`
- **API URL:** set `NEXT_PUBLIC_API_BASE_URL` in `frontend/.env.local`
- Views: Upload → Processing → Results (or Error)
- Results display: metadata cards, line items table with category pills, totals card
- Badges: extraction method (`PDF` / `Vision (scanned)`), tax exempt reason

### 10. Requirements
```
# requirements.txt (deployed to Lambda)
openai>=1.0.0
pymupdf>=1.23.0
boto3>=1.34.0

# requirements-dev.txt (local only)
pytest>=8.0.0
moto[s3,dynamodb,ssm]>=5.0.0
python-dotenv>=1.0.0
pytest-cov>=5.0.0
```

---

## Key Design Decisions
- **SSM Parameter Store for API key**: Key is encrypted at rest, fetched once at Lambda cold start, never appears in CloudFormation parameters or Lambda console env vars in plaintext
- **CloudWatch Alarm**: Metric filter on Lambda log group emits an `InvoiceProcessingErrors` metric on any `ERROR` log line; alarm fires at ≥1 error in 5 minutes — all within free tier (10 custom metrics + 10 alarms free)
- **API Gateway Lambda Proxy**: Lambda handles both routes in one function — routes by `event['httpMethod']` and `event['resource']`
- **Binary media type**: API Gateway configured with `multipart/form-data` as binary media type so PDF bytes pass through correctly
- **Two-stage extraction**: PyMuPDF first (fast, free) → Vision fallback when text is sparse (< 50 chars); confirmed necessary by scanned invoices in sample set
- **GPT-4o parses structure, not code**: no column-index assumptions; handles varying layouts, embedded QTY/ID fields, and missing `$` signs across all vendors
- **Two-type tax exemption detection in system prompt**: agent reads entire invoice including comments/footers before classifying — distinguishes between `pre_taxed` (tax already applied by vendor) and `used_products` (secondhand goods, not subject to sales tax); both set all line item tax to 0 and short-circuit classification. Unknown notices preserved verbatim in `tax_exempt_reason`
- **`quantity` and `unit_price` are Optional**: not all vendors provide them as separate fields; `total_amount` is always required
- **Tax CSV loaded once** at Lambda cold start, not per invocation
- **OpenAI tool use** makes it genuinely agentic — the LLM decides which tools to call and in what order
- **DynamoDB for retrieval**: `GET /invoices/{id}` hits DynamoDB directly; S3 stores raw PDFs only

---

## Verification
1. Store API key: `aws ssm put-parameter --name /retailco/openai-api-key --value <key> --type SecureString`
2. Deploy stack: `aws cloudformation deploy --template-file infrastructure/template.yaml --stack-name retailco-agent --capabilities CAPABILITY_IAM`
3. Get API URL from stack outputs
4. Upload an invoice: `curl -X POST <api-url>/invoices -F "file=@Invoices/RetailCo_Invoice.pdf"`
5. Verify response contains line-item tax breakdown
6. Fetch stored result: `curl <api-url>/invoices/<invoice_id>`
7. Check Lambda logs in CloudWatch for agent tool call trace
