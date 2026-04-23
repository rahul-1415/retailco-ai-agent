# RetailCo Invoice Tax Agent — Design Decisions

A record of every significant technical and product decision made during the design and build of this system, with the reasoning behind each choice.

---

## Infrastructure & AWS

### API Gateway over S3-event trigger
**Decision:** Use API Gateway as the system entry point instead of an S3 `ObjectCreated` event.
**Why:** S3-event-driven requires manually dropping files into a bucket — not demonstrable as a service. API Gateway exposes a real HTTP endpoint any client can call. Matches how a real AP integration would work.

### Synchronous processing (no SQS/async)
**Decision:** `POST /invoices` processes the PDF inline and returns the result in the same HTTP response.
**Why:** Simpler to build and demo. The 29-second API Gateway timeout is sufficient for the invoice sizes in scope. Async (SQS + polling) adds complexity with no requirement gain at this scale.

### Single Lambda function for both routes
**Decision:** One Lambda handles `POST /invoices` and `GET /invoices/{id}`, routing on `event['httpMethod']`.
**Why:** Reduces CloudFormation resources, IAM roles, and cold-start surface area. Both routes share the same DynamoDB client and classifier — no duplication.

### SSM Parameter Store over Secrets Manager or CloudFormation parameter
**Decision:** OpenAI API key stored as SSM `SecureString`, fetched by Lambda at cold start.
**Why:** Secrets Manager costs $0.40/secret/month — SSM standard tier is free. CloudFormation parameters expose the key in stack history and the Lambda console. SSM encrypts at rest with KMS, never appears in plaintext in AWS UI.

### SSM key cached at module scope
**Decision:** Lambda fetches the key once on cold start and caches it in a module-level variable.
**Why:** Eliminates one SSM API call per invocation. SSM has a per-request cost and latency; caching is the standard pattern for Lambda cold-start config.

### DynamoDB PAY_PER_REQUEST billing
**Decision:** No provisioned capacity — PAY_PER_REQUEST on the `tax_results` table.
**Why:** Free tier covers 25 RCU/WCU provisioned, but PAY_PER_REQUEST is simpler and cheaper at low/unpredictable volume. No capacity planning needed.

### CloudWatch Alarm via Metric Filter (not Lambda Destinations)
**Decision:** CloudWatch Logs Metric Filter on `ERROR` pattern → CloudWatch Alarm → SNS.
**Why:** All free tier. Metric filters work on existing CloudWatch Logs with zero code change. Lambda Destinations would require async invocation and add complexity.

### Lambda packaged as S3 zip, not CloudFormation ZipFile
**Decision:** `Code: S3Bucket/S3Key` referencing a pre-uploaded `lambda.zip`, not `Code: ZipFile`.
**Why:** `ZipFile` only supports inline code with no imports — it cannot bundle `src/`, PyMuPDF, or OpenAI SDK. A zip uploaded to S3 is the standard pattern for any Lambda with dependencies. `scripts/deploy.sh` automates the build, upload, and deploy in one command.

### Dedicated S3 packaging bucket with public access blocked
**Decision:** A separate `retailco-cfn-<account-id>` bucket holds `lambda.zip`. All public access is blocked on creation.
**Why:** Keeping deployment artifacts out of the invoices bucket makes IAM policies and lifecycle rules cleaner. Public access block is a mandatory baseline — there is no reason for a packaging bucket to be public, and misconfigured bucket policies have caused significant real-world data breaches.

### `deploy.sh` over SAM CLI or CDK
**Decision:** A plain bash script using `aws cloudformation deploy` directly.
**Why:** SAM and CDK add toolchain dependencies (Docker for SAM local, Node for CDK) that aren't needed here. The project is a single Lambda with a known structure — a 60-line bash script is fully transparent, requires only the AWS CLI, and is easier to audit and modify than a framework abstraction.

### `--platform manylinux2014_x86_64` for pip installs
**Decision:** All `pip install` calls targeting Lambda use `--platform manylinux2014_x86_64 --only-binary=:all:`.
**Why:** Packages like `pydantic_core` (a dependency of `openai`) ship platform-specific compiled extensions. Running `pip install` on macOS downloads macOS `.dylib` files which cannot load on Lambda's Amazon Linux environment, causing `ImportModuleError` at cold start. The `manylinux` wheels are built for Linux glibc compatibility and work on Lambda.

### Explicit `aws lambda update-function-code` after every deploy
**Decision:** `deploy.sh` always runs `aws lambda update-function-code` after CloudFormation deploy.
**Why:** CloudFormation only redeploys the Lambda if the template changes. When only the zip contents change (new code, updated dependencies), CloudFormation reports "No changes to deploy" and the old Lambda code stays live. The explicit update-function-code call forces Lambda to pull the latest zip from S3 regardless.

### Explicit `LambdaLogGroup` CloudFormation resource
**Decision:** Lambda log group created as an explicit `AWS::Logs::LogGroup` resource with `RetentionInDays: 30`, rather than relying on auto-creation.
**Why:** Lambda log groups are created automatically on first invocation, not at stack creation time. The `ErrorMetricFilter` resource needs the group to exist at deploy time — without the explicit resource it fails with "log group does not exist". Explicit creation also enforces a 30-day retention policy; auto-created groups have no retention limit and accumulate indefinitely.

### CORS headers on all Lambda responses + OPTIONS methods in API Gateway
**Decision:** `lambda_handler.py` returns `Access-Control-Allow-Origin: *` on every response, plus a dedicated `_cors_preflight()` handler for OPTIONS. API Gateway has explicit OPTIONS methods on both resources.
**Why:** The frontend is hosted on a different domain (Vercel). Without CORS headers, browsers block all cross-origin requests. When Lambda returns a 502, API Gateway substitutes its own error response which has no CORS headers — so even the error is blocked by the browser, masking the real failure. Handling OPTIONS in Lambda (rather than API Gateway mock) keeps all CORS logic in one place.

### GitHub Actions CI/CD with `environment: production` approval gate
**Decision:** Two-job pipeline — `build` runs automatically on push, `deploy` is gated behind a GitHub Environment with required reviewers.
**Why:** Automatic deploys to production on every push are risky — a bad commit would go live immediately. The `environment: production` gate pauses the pipeline and sends an approval notification, giving a human a chance to review the build before it touches AWS. The build job still runs automatically so the artifact is ready and waiting; the approval only adds a human step before the actual `cloudformation deploy`.

---

## Extraction & AI

### Two-stage PDF extraction (PyMuPDF → Vision fallback)
**Decision:** Try PyMuPDF text extraction first; fall back to GPT-4o Vision if text is fewer than 50 characters.
**Why:** PyMuPDF is free and instant for native PDFs. Vision costs ~$0.006/page. Confirmed necessary by `Invoice_Scan.pdf` — a genuine scan with handwritten-style font that yields zero usable text from PyMuPDF.

### GPT-4o for both extraction and classification
**Decision:** Use GPT-4o for all LLM calls (text parsing, vision, classification).
**Why:** Single model, consistent JSON output quality, vision capability built in. No need to manage multiple model versions.

### LLM parses invoice structure, not code
**Decision:** No column-index assumptions in the extractor. GPT-4o receives the full text and returns structured JSON.
**Why:** Invoices from different vendors have different column orders (BetaShipping: `Qty | Price | Desc | Amount` vs AlphaImports: `Desc | Qty | Price | Amount`) and some embed quantity inside the description string (Delta-Distribution). Hardcoded parsing would break on any vendor variation. LLM handles all formats naturally.

### `quantity` and `unit_price` are Optional
**Decision:** Both fields are `Optional[float]` on `LineItem` and `LineItemTax`.
**Why:** Delta-Distribution invoices have only two columns (Description | Total Price) with QTY and unit price embedded in the description text. Some invoices only provide a line total. `total_amount` is always required; the others are best-effort.

### Tax CSV loaded once at cold start
**Decision:** `TaxClassifier` reads `tax_rate_by_category.csv` once during Lambda cold start, held in memory for all subsequent invocations.
**Why:** 50-row CSV is tiny (~2KB). Re-reading from disk on every invocation adds latency with no benefit. Lambda instances are reused across invocations within the same execution environment.

### Two-type tax exemption model
**Decision:** `tax_exempt: bool` + `tax_exempt_reason: Optional[str]` with two known values: `"pre_taxed"` and `"used_products"`.
**Why:** Invoices can be zero-tax for legally distinct reasons. "Pre-taxed" means the vendor already remitted tax — RetailCo must not double-tax. "Used products" means the goods are legally exempt regardless. Collapsing both into a single flag loses audit trail. The reason is stored in DynamoDB for AP team review.

### Agent short-circuits on tax_exempt
**Decision:** If `tax_exempt=True`, the classification loop is skipped entirely — all line items get `tax_rate=0` without calling GPT-4o.
**Why:** Saves ~$0.01 in API calls per exempt invoice. More importantly, it's semantically correct — classifying line items on a pre-taxed invoice and assigning 0% is misleading; the correct signal is that tax is inapplicable, not that every category happens to be zero-rated.

---

## Data & Models

### `Address` as a separate dataclass
**Decision:** Vendor and bill-to addresses are stored as an `Address` object with sub-fields (`street`, `city`, `state`, `zip_code`, `phone`), not a single string.
**Why:** Structured sub-fields are queryable in DynamoDB and renderable cleanly in the frontend. A flat string would require re-parsing if the AP team wanted to filter by state or city later.

### Optional metadata fields (vendor address, bill-to, customer ID, due date)
**Decision:** These fields are captured and stored but not required for the core tax calculation.
**Why:** Every sample invoice contains this information. Storing it costs nothing extra in DynamoDB and gives the AP team full invoice context without needing to re-open the original PDF. Fields are `Optional` so missing data doesn't break processing.

### `TaxResult.to_dict()` for serialisation
**Decision:** `TaxResult` owns its own serialisation via `to_dict()` rather than using a library like Pydantic.
**Why:** Keeps dependencies minimal (no Pydantic in Lambda package). The model is simple enough that manual serialisation is readable and maintainable. `to_dict()` also handles `Address` → `dict` conversion and `Decimal` compatibility for DynamoDB.

---

## Data Quality

### CSV encoding: Home Décor → Home Decor
**Decision:** Changed row 30 of `tax_rate_by_category.csv` from `Home Décor` (Latin-1 encoded `é`) to `Home Decor` (plain ASCII).
**Why:** The file was opened with `encoding="utf-8"` which raised `UnicodeDecodeError` on the `é` byte. Two options: change the open encoding to `latin-1`, or fix the source data. Fixed the source — the accent is cosmetic, the category meaning is unchanged, and keeping the codebase ASCII-clean avoids future encoding surprises.

---

## Development Practices

### No dotenv in deployed code
**Decision:** `python-dotenv` is only imported in `tests/conftest.py` and `scripts/test_local.py`, never in `src/` or `lambda_handler.py`.
**Why:** The deployed Lambda gets its config from environment variables set by CloudFormation and SSM. Importing dotenv in deployed code is misleading and could mask misconfiguration in production.

### `src/config.py` env-var fallback pattern
**Decision:** `get_openai_key()` checks `OPENAI_API_KEY` env var first; falls back to SSM only if absent.
**Why:** Locally, the key is set directly in `.env` (via dotenv in the test/script layer). On AWS, `OPENAI_API_KEY` is not set so SSM is used. Same code, no conditionals, no dev-only branches in deployed files.

### Two requirements files
**Decision:** `requirements.txt` (deployed to Lambda) and `requirements-dev.txt` (local only).
**Why:** `moto`, `pytest`, and `python-dotenv` must never be packaged into the Lambda deployment. Separate files make the boundary explicit and prevent accidental inclusion.

### `scripts/test_local.py` for local pipeline testing
**Decision:** A standalone script that runs extraction → classification → calculation without any AWS services.
**Why:** The full `InvoiceAgent` requires DynamoDB and S3. For iterating on prompts and extraction quality, a script that bypasses AWS lets you test the entire LLM pipeline locally against any PDF with a single command.

---

## Frontend

### Next.js over plain HTML
**Decision:** Replaced initial `frontend/index.html` (Tailwind CDN + vanilla JS) with Next.js 14 + TypeScript + Tailwind.
**Why:** Modular component structure makes the frontend maintainable as it grows. TypeScript catches mismatches between API response shape and UI rendering at compile time. Next.js adds zero complexity for a single-page app but gives a proper build pipeline for deployment.

### Single page, view-state machine
**Decision:** One page (`app/page.tsx`) manages a `view` state: `upload | processing | error | results`. No routing.
**Why:** The workflow is linear — upload → process → view result. Multi-page routing adds navigation complexity with no UX benefit for a single-flow tool.

### API URL via environment variable
**Decision:** `NEXT_PUBLIC_API_BASE_URL` in `.env.local` controls the backend endpoint.
**Why:** Same frontend code works against SAM local (`http://127.0.0.1:3000`), a dev stack, and the production API Gateway URL — no code changes, just env var swap.

### Invoice history via `GET /invoices` scan, not a separate index
**Decision:** `GET /invoices` runs a DynamoDB `Scan` with `ProjectionExpression` for summary fields. No secondary index, no separate history table.
**Why:** At AP-team scale (dozens to low hundreds of invoices) a scan is instant and free. A GSI or a separate history table would add CloudFormation resources and write overhead for no measurable gain. If the table ever grows to thousands of records, a GSI on `date` can be added then.

### History panel returns summary fields only
**Decision:** `GET /invoices` returns `invoice_id`, `vendor`, `date`, `grand_total`, `tax_exempt`, `tax_exempt_reason` — not the full `TaxResult`.
**Why:** The full result (including all line items) can be hundreds of bytes per record. The history list only needs enough to render a row and identify the record. Full detail is fetched on demand when the user clicks a row (`GET /invoices/{id}`).
