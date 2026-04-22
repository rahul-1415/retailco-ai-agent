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
├── docs/
│   ├── plan.md                 # This file — current implementation plan
│   └── plan-history.md         # Full record of planning decisions and changes
├── tax_rate_by_category.csv
├── Invoices/                   # Sample invoices
├── requirements.txt
├── .env
└── .gitignore
```

---

## Implementation Steps

### 1. Models (`src/models/`)
- `LineItem`: `description`, `quantity`, `unit_price`, `total_amount`
- `Invoice`: `invoice_id`, `vendor`, `date`, `line_items: list[LineItem]`
- `LineItemTax`: `line_item`, `category`, `tax_rate`, `tax_amount`
- `TaxResult`: `invoice_id`, `line_item_taxes`, `subtotal`, `total_tax`, `grand_total`

### 2. Extractors (`src/extractors/`)
- `BaseExtractor`: abstract `extract(pdf_bytes) -> Invoice`
- `PDFExtractor`: uses **PyMuPDF** (`fitz`) to extract text from native PDFs, parses into `Invoice`
- `VisionExtractor`: sends PDF page as base64 image to OpenAI GPT-4o vision; structured JSON response parsed into `Invoice`
- Auto-detection: try `PDFExtractor` first (fast, free); fall back to `VisionExtractor` if text is sparse/empty

### 3. Classifier (`src/classifier/tax_classifier.py`)
- Loads `tax_rate_by_category.csv` into memory on cold start
- Exposed as an **OpenAI tool**: `classify_line_item(description: str) -> {category, tax_rate}`
- Uses GPT-4o to semantically match description to the closest of the 50 categories

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

**Agent loop (`invoice_agent.py`):**
1. Receive PDF bytes
2. Call `extract_invoice_data` tool
3. For each line item, call `classify_line_item`
4. Call `calculate_line_tax` for each
5. Call `save_result` with final `TaxResult`
6. Return `TaxResult` to caller

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

### 9. Requirements (`requirements.txt`)
```
openai>=1.0.0
pymupdf>=1.23.0
boto3>=1.34.0
```

---

## Key Design Decisions
- **SSM Parameter Store for API key**: Key is encrypted at rest, fetched once at Lambda cold start, never appears in CloudFormation parameters or Lambda console env vars in plaintext
- **CloudWatch Alarm**: Metric filter on Lambda log group emits an `InvoiceProcessingErrors` metric on any `ERROR` log line; alarm fires at ≥1 error in 5 minutes — all within free tier (10 custom metrics + 10 alarms free)
- **API Gateway Lambda Proxy**: Lambda handles both routes in one function — routes by `event['httpMethod']` and `event['resource']`
- **Binary media type**: API Gateway configured with `multipart/form-data` as binary media type so PDF bytes pass through correctly
- **Two-stage extraction**: PyMuPDF first (fast, free) → Vision fallback (handles scanned invoices)
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
