# RetailCo Invoice Tax Agent

An agentic AI service that automates invoice tax classification for the RetailCo Accounts Payable team. Upload a PDF invoice (native or scanned), and the system extracts every line item, classifies each to one of 50 tax categories using GPT-4o, calculates taxes, and returns a structured JSON result — all in a single API call.

## Architecture

```
  POST /invoices        ┌─────────────────────────────────────────────┐
  (multipart PDF) ─────►│  API Gateway  →  Lambda (Python 3.12)       │
                        │                      │                       │
  GET /invoices/{id}    │                      ├─► S3  (raw PDF)       │
  GET /invoices   ─────►│                      │                       │
                        │                      ▼                       │
                        │                 GPT-4o Agent                 │
                        │                 ┌────┴────┐                  │
                        │                Extract  Classify             │
                        │                  │        │                  │
                        │                  └────┬───┘                  │
                        │                       ▼                      │
                        │                  DynamoDB                    │
                        │                  (tax_results)               │
                        └─────────────────────────────────────────────┘
```

**PDF extraction** — PyMuPDF for native PDFs; automatic fallback to GPT-4o Vision for scanned/image-only PDFs.

**Tax classification** — GPT-4o matches each line item description to the closest of 50 categories from `tax_rate_by_category.csv`.

**Deployed on AWS Free Tier** via a single CloudFormation stack (API Gateway + Lambda + DynamoDB + S3 + SSM + CloudWatch).

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/invoices` | Upload a PDF (`multipart/form-data`, field `file`). Returns full `TaxResult` JSON. |
| `GET` | `/invoices/{invoice_id}` | Fetch a previously processed result by ID. |
| `GET` | `/invoices` | List all processed invoices (summary fields only, sorted by date). |

### Example response (`POST /invoices`)

```json
{
  "invoice_id": "INV-2024-0042",
  "vendor": "Alpha Imports LLC",
  "date": "2024-11-15",
  "tax_exempt": false,
  "subtotal": 5240.00,
  "total_tax": 471.60,
  "grand_total": 5711.60,
  "line_item_taxes": [
    {
      "description": "Wireless Bluetooth Headphones (x10)",
      "category": "Electronics",
      "tax_rate": 0.08,
      "tax_amount": 240.00,
      "total_amount": 3000.00
    }
  ]
}
```

## Project Structure

```
retailco-ai-agent/
├── src/
│   ├── models/          # LineItem, Invoice, TaxResult, LineItemTax dataclasses
│   ├── extractors/      # PDFExtractor (PyMuPDF) + VisionExtractor (GPT-4o)
│   ├── classifier/      # TaxClassifier — CSV-backed, GPT-4o semantic matching
│   ├── calculator/      # Tax calculation (pure functions)
│   └── agent/           # InvoiceAgent — OpenAI tool-use orchestrator
├── lambda_handler.py    # AWS Lambda entry point (routes POST + GET)
├── infrastructure/
│   └── template.yaml    # CloudFormation — all AWS resources
├── frontend/            # Next.js 14 + TypeScript + Tailwind UI
├── scripts/
│   ├── deploy.sh        # One-command build + deploy to AWS
│   └── local_server.py  # Local dev server (no AWS needed)
├── tests/               # pytest unit tests (moto for DynamoDB)
├── tax_rate_by_category.csv
└── requirements.txt
```

## Local Development

### Backend (no AWS required)

```bash
# Install dependencies
pip install -r requirements-dev.txt

# Set OpenAI key
echo "OPENAI_API_KEY=sk-..." > .env

# Start local server on :3001
python scripts/local_server.py
```

### Frontend

```bash
cd frontend
npm install

# Point at local server
echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:3001" > .env.local

npm run dev   # http://localhost:3000
```

### Run tests

```bash
pytest tests/ -v
```

### Test the full pipeline locally against a PDF

```bash
python scripts/test_local.py Invoices/RetailCo_Invoice.pdf
```

## AWS Deployment

### One-time setup

```bash
# Store your OpenAI key in SSM (never in code or CloudFormation)
aws ssm put-parameter \
  --name /retailco/openai-api-key \
  --value "sk-..." \
  --type SecureString
```

### Deploy

```bash
./scripts/deploy.sh
```

This script:
1. Creates a private S3 packaging bucket (`retailco-cfn-<account-id>`)
2. Installs Lambda dependencies using `manylinux2014_x86_64` wheels (Linux-compatible)
3. Builds and uploads `lambda.zip` to S3
4. Deploys (or updates) the CloudFormation stack
5. Forces Lambda to pull the new zip regardless of template changes
6. Prints the live API URL

### Connect the frontend

After deploy, copy the `ApiUrl` from the script output and set it in Vercel (or `frontend/.env.local`):

```
NEXT_PUBLIC_API_BASE_URL=https://<id>.execute-api.us-east-1.amazonaws.com/prod
```

## CI/CD

GitHub Actions runs on every push to `main` (when `src/`, `lambda_handler.py`, `requirements.txt`, or `infrastructure/template.yaml` change):

1. **Build** — installs dependencies, creates zip, validates CloudFormation template, uploads to S3
2. **Deploy** — pauses for manual approval (GitHub Environment: `production`), then deploys to AWS

Required repository secrets: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_ACCOUNT_ID`

## Tech Stack

| Layer | Technology |
|---|---|
| Runtime | Python 3.12 on AWS Lambda |
| AI | OpenAI GPT-4o (tool use + vision) |
| PDF extraction | PyMuPDF (native), GPT-4o Vision (scanned) |
| API | AWS API Gateway (REST, Lambda Proxy) |
| Storage | DynamoDB (results) + S3 (raw PDFs) |
| Config | AWS SSM Parameter Store (SecureString) |
| Monitoring | CloudWatch Logs + Metric Filter + SNS alarm |
| IaC | AWS CloudFormation |
| Frontend | Next.js 14 + TypeScript + Tailwind CSS (Vercel) |
| CI/CD | GitHub Actions |
