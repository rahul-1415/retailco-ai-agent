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
