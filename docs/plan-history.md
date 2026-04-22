# RetailCo Invoice Tax Agent — Planning History

A chronological record of all planning decisions, changes, and rationale made during the design of this system.

---

## v1 — Initial Plan (2026-04-22)

### What was decided
The core system design was established:

- **Trigger:** S3 `ObjectCreated` event — invoice PDF dropped into an S3 bucket fires a Lambda
- **LLM:** OpenAI GPT-4o (API key already available in `.env`)
- **Extraction:** Two-stage — PyMuPDF for native-text PDFs, OpenAI Vision fallback for scanned/image PDFs
- **Classification:** GPT-4o matches each line item description to one of 50 tax categories from `tax_rate_by_category.csv`
- **Storage:** DynamoDB for queryable results, S3 for full JSON output
- **IaC:** Single CloudFormation YAML
- **Agentic pattern:** OpenAI tool use (function calling) — four tools: `extract_invoice_data`, `classify_line_item`, `calculate_line_tax`, `save_result`

### Project structure established
```
src/models/, src/extractors/, src/classifier/, src/calculator/, src/agent/
lambda_handler.py
infrastructure/template.yaml
```

### Key constraints noted
- AWS Free Tier only
- Clean, modular OOP code
- CloudFormation deployment required
- Fully agentic (LLM-driven tool use, not scripted pipeline)

---

## v2 — API Gateway Added (2026-04-22)

### What changed
Replaced the S3-event trigger with **API Gateway** as the system entry point.

### Why
S3-event-driven requires manually dropping files into a bucket, which is not demonstrable as a service. API Gateway exposes a real HTTP endpoint that any client or reviewer can call directly — much cleaner for demo and closer to a production service pattern.

### Decision: Sync vs Async processing
Two approaches were considered:

| Approach | Description | Trade-off |
|---|---|---|
| **Sync (chosen)** | `POST /invoices` processes inline, returns TaxResult in the HTTP response | Simple, immediately demonstrable; risks 29s API Gateway timeout on complex invoices |
| Async | `POST /invoices` returns `{invoice_id, status: processing}` immediately; S3 event triggers processing; client polls `GET` | Robust for slow invoices; adds complexity with no requirement gain |

Sync was chosen — simpler to build, easier to demo, sufficient for the invoice sizes in scope.

### Endpoints added
| Method | Path | Description |
|---|---|---|
| `POST` | `/invoices` | Upload PDF (multipart/form-data), returns TaxResult JSON |
| `GET` | `/invoices/{invoice_id}` | Fetch stored result from DynamoDB |

### CloudFormation resources added
- `InvoiceApi` (RestApi), `InvoicesResource`, `InvoiceIdResource`
- `PostMethod`, `GetMethod`
- `ApiDeployment` (prod stage)
- `LambdaApiPermission`
- Binary media type: `multipart/form-data` configured on API Gateway

### Lambda handler updated
- Now routes on `event['httpMethod']` — one function handles both endpoints
- Returns API Gateway-compatible response format (`statusCode`, `headers`, `body`)
- `POST`: parses multipart body → extracts PDF bytes → runs agent → returns JSON
- `GET`: reads DynamoDB → returns stored result

---

## v3 — SSM Parameter Store for OpenAI Key (2026-04-22)

### What changed
Moved OpenAI API key storage from CloudFormation parameter / Lambda environment variable to **AWS SSM Parameter Store (SecureString)**.

### Why
The original plan passed `OpenAIApiKey` as a CloudFormation parameter, which means it appears in:
- CloudFormation console parameter history
- Lambda environment variables (visible in AWS console)

SSM Parameter Store with `SecureString` type encrypts the key at rest using AWS KMS (default key, free). The key never touches CloudFormation and is not visible in the Lambda console.

### How it works
- Parameter stored once manually: `aws ssm put-parameter --name /retailco/openai-api-key --value <key> --type SecureString`
- Lambda IAM role granted `ssm:GetParameter` on that specific parameter ARN only (least privilege)
- Lambda fetches the key **once at cold start**, caches in module scope — no per-invocation SSM call
- CloudFormation stack has no `OpenAIApiKey` parameter — deploy command is cleaner

### CloudFormation changes
- Removed `OpenAIApiKey` parameter
- Added `ssm:GetParameter` to `LambdaExecutionRole` policy
- Lambda env var now holds the **parameter name** (`/retailco/openai-api-key`), not the key value

---

## v4 — CloudWatch Alarm Added (2026-04-22)

### What changed
Added a **CloudWatch Metric Filter + Alarm** on Lambda error logs.

### Why
Without monitoring, a failed invocation (OpenAI timeout, malformed PDF, DynamoDB error) is silent unless someone checks CloudWatch logs manually. A metric filter on `ERROR` log patterns surfaces failures as a CloudWatch metric, and an alarm notifies when the error rate crosses a threshold.

### What was added
- **CloudWatch Log Metric Filter**: scans Lambda log group for `ERROR` pattern, emits a custom metric `InvoiceProcessingErrors`
- **CloudWatch Alarm**: triggers when `InvoiceProcessingErrors >= 1` in a 5-minute window
- **SNS Topic**: alarm publishes to an SNS topic; email subscription can be added post-deploy
- All within AWS Free Tier (10 custom metrics, 10 alarms free)

### CloudFormation resources added
- `ErrorMetricFilter` (`AWS::Logs::MetricFilter`)
- `ErrorAlarm` (`AWS::CloudWatch::Alarm`)
- `AlarmTopic` (`AWS::SNS::Topic`)

---

## Current State (v4)

### AWS Services in use (all Free Tier)
| Service | Purpose |
|---|---|
| API Gateway | HTTP entry point — `POST /invoices`, `GET /invoices/{id}` |
| Lambda | Invoice processing, routing, agent orchestration |
| S3 | Raw PDF storage |
| DynamoDB | Tax result storage and retrieval |
| SSM Parameter Store | Encrypted OpenAI API key storage |
| CloudWatch Logs | Lambda execution logs |
| CloudWatch Alarms | Error rate monitoring |
| SNS | Alarm notification delivery |
| CloudFormation | Full infrastructure as code |

### Services considered but not included
| Service | Reason not included |
|---|---|
| SQS | Only useful for async pattern; sync was chosen |
| Step Functions | OpenAI tool use already provides agentic orchestration |
| X-Ray | Useful for tracing but not essential for requirements |
| Secrets Manager | $0.40/secret/month; SSM does the same job for free |
| API Gateway Usage Plan | Adds rate limiting but no requirement calls for it |

---

## v5 — Invoice Reality Check: Pre-Taxed Detection + Optional Fields (2026-04-22)

### What prompted this
Actual invoice files were reviewed before building. Four issues were found that the plan didn't account for.

### Finding 1: Pre-taxed invoice (Delta-Distribution, R-1093-12322)
The invoice comments section reads: *"Do not tax, tax has already been applied to items in invoice."* Without handling this, the agent would silently double-tax the invoice — a correctness bug, not a cosmetic one.

**Change:** Agent system prompt now includes explicit tax exemption detection with two distinct types (see v6 below for the expansion of this).

### Finding 2: Quantity and price embedded in description (Delta-Distribution)
Delta-Distribution uses only two columns (Description | Price) and embeds quantity and product ID inside the description string: `"BrightWave Laundry Pods – 42 Count – ID: 68840 - QTY: 50 $799.50"`. The original `LineItem` model assumed `quantity` and `unit_price` were always separate fields.

**Change:** `quantity: Optional[float]` and `unit_price: Optional[float]` in `LineItem` — both nullable. The GPT-4o extraction prompt now explicitly instructs the model to parse these fields out of the description string when column-based values are absent, and return `null` when they genuinely cannot be determined.

### Finding 3: Scanned invoice confirmed (Invoice_Scan.pdf)
The scan is a genuine image-based PDF with handwritten-style font and OCR noise (`"aO"` for `30`, `"f"` for `$`). PyMuPDF will produce no usable text. This confirms the Vision fallback is essential, not optional.

**Change:** Fallback threshold made explicit — trigger `VisionExtractor` when extracted text is fewer than 50 meaningful characters.

### Finding 4: Inconsistent $ formatting
Several invoices (AlphaImportInvoice, 1.pdf) drop the `$` prefix on the last few amount rows. No model change needed — GPT-4o handles this in context — but the extraction prompt was updated to explicitly instruct amount parsing as float after stripping non-numeric characters.

### Summary of model changes
| Field | Before | After |
|---|---|---|
| `LineItem.quantity` | `int` (required) | `Optional[float]` |
| `LineItem.unit_price` | `float` (required) | `Optional[float]` |
| `Invoice.pre_taxed` | not present | `bool` (required) — later replaced in v6 |
| `TaxResult.pre_taxed` | not present | `bool` (required) — later replaced in v6 |
| `TaxResult.extraction_method` | not present | `str` (`"pdf"` or `"vision"`) |

---

## v6 — Two-Type Tax Exemption Model (2026-04-22)

### What prompted this
After v5 added `pre_taxed: bool`, it was noted that invoices can be zero-tax for two fundamentally different reasons:
1. **Pre-taxed** — the vendor already applied tax, so RetailCo must not add tax again
2. **Used/non-taxable goods** — items are secondhand or refurbished, which are legally exempt from sales tax regardless of who handled them previously

These are different business scenarios. Collapsing them into a single `pre_taxed` bool loses the reason, which matters for accounting and audit purposes.

### What changed

**Model:** `Invoice.pre_taxed: bool` replaced by:
- `Invoice.tax_exempt: bool`
- `Invoice.tax_exempt_reason: Optional[str]`

Same change propagated to `TaxResult`.

**Agent system prompt:** Detection rule now explicitly distinguishes the two types:

| Type | `tax_exempt_reason` value | Example notice phrases |
|---|---|---|
| Pre-taxed | `"pre_taxed"` | "Do not tax, tax has already been applied", "Tax included" |
| Used goods | `"used_products"` | "Items are non-taxable due to 'Used' status", "Secondhand — no tax applicable" |
| Unknown | raw notice text | Any exemption notice that doesn't match the above patterns |

**Agent behaviour:** Unchanged — if `tax_exempt=True` for any reason, classification is skipped and all line items receive `tax_rate=0`. The reason is carried through to `TaxResult` and stored in DynamoDB.

### Summary of model changes (v6)
| Field | Before (v5) | After (v6) |
|---|---|---|
| `Invoice.pre_taxed` | `bool` | removed |
| `Invoice.tax_exempt` | not present | `bool` (required) |
| `Invoice.tax_exempt_reason` | not present | `Optional[str]` |
| `TaxResult.pre_taxed` | `bool` | removed |
| `TaxResult.tax_exempt` | not present | `bool` (required) |
| `TaxResult.tax_exempt_reason` | not present | `Optional[str]` |

---

## v7 — Optional Invoice Metadata Fields (2026-04-22)

### What prompted this
During the build phase, the decision was made to capture richer invoice context beyond the minimum required for tax calculation — vendor address, bill-to details, customer ID, and due date are present in every sample invoice and useful for AP team auditing.

### What changed
- `Address` dataclass added: `street`, `city`, `state`, `zip_code`, `phone` — all optional
- `Invoice` gains: `vendor_address`, `bill_to_name`, `bill_to_address`, `customer_id`, `due_date`
- `TaxResult` mirrors all new fields and serialises them in `to_dict()`
- Extraction prompt updated to request all new fields; GPT-4o returns `null` for any not present
- Both `PDFExtractor` and `VisionExtractor` get `_to_address()` helper
- `TaxCalculator` passes all metadata straight through to `TaxResult`

---

## v8 — CSV Encoding Fix: Home Décor → Home Decor (2026-04-22)

### What prompted this
Running `scripts/test_local.py` against a real invoice raised `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe9`. The CSV file `tax_rate_by_category.csv` contained `Home Décor` (row 30) with a Latin-1 encoded `é` character, incompatible with the UTF-8 `open()` call in `TaxClassifier`.

### Options considered
1. Change `open()` encoding to `latin-1` — works but masks future encoding issues
2. Fix the CSV to use plain ASCII — correct at the source, no code change needed

**Decision:** Fix the CSV. Changed `Home D\xe9cor` → `Home Decor`. The category name is unchanged in meaning; the accent was cosmetic. Code stays clean.

---

## v9 — Next.js Frontend (2026-04-22)

### What prompted this
Initial frontend was a single `frontend/index.html` using Tailwind CDN + vanilla JS. Replaced with a proper Next.js 14 app for modularity, TypeScript safety, and easier maintainability.

### What changed
- Framework: Next.js 14 + TypeScript + Tailwind CSS (via PostCSS)
- App Router with a single client page (`app/page.tsx`) managing view state
- Components split by responsibility:
  - `Header` — nav + lookup input
  - `UploadPanel` — drag-drop zone, file card, process button
  - `ProcessingPanel` — spinner + rotating step labels
  - `ErrorPanel` — error card + retry
  - `results/ResultsPanel` — top bar, badges, composes sub-components
  - `results/MetadataCards` — 8-cell metadata grid
  - `results/LineItemsTable` — line items table with category pills
  - `results/TotalsCard` — subtotal / tax / grand total
- `lib/types.ts` — TypeScript interfaces matching Python models exactly
- `lib/api.ts` — `processInvoice()` and `lookupInvoice()` fetch wrappers
- `lib/format.ts` — shared `fmt()`, `fmtAddress()`, `TAX_EXEMPT_LABELS`
- API base URL via `NEXT_PUBLIC_API_BASE_URL` env var; defaults to SAM local port
