#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# deploy.sh — Build Lambda package and deploy CloudFormation stack
#
# Usage:
#   ./scripts/deploy.sh
#
# Prerequisites:
#   - AWS CLI configured (aws configure)
#   - OpenAI key stored: aws ssm put-parameter --name /retailco/openai-api-key --value sk-... --type SecureString
# ---------------------------------------------------------------------------
set -euo pipefail

STACK_NAME="retailco-agent"
REGION="us-east-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
CFN_BUCKET="retailco-cfn-${ACCOUNT_ID}"
TEMPLATE="infrastructure/template.yaml"
BUILD_DIR=".build"

echo "==> Account : $ACCOUNT_ID"
echo "==> Region  : $REGION"
echo "==> Stack   : $STACK_NAME"
echo ""

# ---------------------------------------------------------------------------
# 1. Ensure CFN packaging bucket exists
# ---------------------------------------------------------------------------
echo "[1/5] Ensuring deployment bucket exists..."
aws s3 mb "s3://${CFN_BUCKET}" --region "$REGION" 2>/dev/null || true
# Block all public access — never expose this bucket
aws s3api put-public-access-block \
  --bucket "$CFN_BUCKET" \
  --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true" \
  2>/dev/null || true

# ---------------------------------------------------------------------------
# 2. Install dependencies into build directory
# ---------------------------------------------------------------------------
echo "[2/5] Installing dependencies (linux/x86_64 wheels for Lambda)..."
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
pip install -r requirements.txt -t "$BUILD_DIR" --quiet \
  --platform manylinux2014_x86_64 \
  --python-version 3.12 \
  --only-binary=:all: \
  --upgrade

# ---------------------------------------------------------------------------
# 3. Copy source code into build directory
# ---------------------------------------------------------------------------
echo "[3/5] Copying source code..."
cp lambda_handler.py "$BUILD_DIR/"
cp tax_rate_by_category.csv "$BUILD_DIR/"
cp -r src "$BUILD_DIR/src"

# ---------------------------------------------------------------------------
# 4. Zip and upload to S3
# ---------------------------------------------------------------------------
echo "[4/5] Packaging and uploading Lambda zip..."
cd "$BUILD_DIR"
zip -r ../lambda.zip . -x "*.pyc" -x "*/__pycache__/*" -x "*.dist-info/*" > /dev/null
cd ..
aws s3 cp lambda.zip "s3://${CFN_BUCKET}/lambda.zip" --region "$REGION"
rm lambda.zip

# ---------------------------------------------------------------------------
# 5. Deploy CloudFormation stack
# ---------------------------------------------------------------------------
echo "[5/5] Deploying CloudFormation stack..."
aws cloudformation deploy \
  --template-file "$TEMPLATE" \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
      DeploymentBucket="$CFN_BUCKET" \
      SsmParamName="/retailco/openai-api-key" \
  --no-fail-on-empty-changeset

# ---------------------------------------------------------------------------
# Force Lambda to pull the new zip (CloudFormation skips if template unchanged)
# ---------------------------------------------------------------------------
echo "[+] Updating Lambda function code..."
aws lambda update-function-code \
  --function-name retailco-invoice-processor \
  --s3-bucket "$CFN_BUCKET" \
  --s3-key lambda.zip \
  --region "$REGION" \
  --output table \
  --query "{FunctionName:FunctionName,CodeSize:CodeSize,LastModified:LastModified}"

# ---------------------------------------------------------------------------
# Print outputs
# ---------------------------------------------------------------------------
echo ""
echo "==> Stack deployed successfully."
echo ""
aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query "Stacks[0].Outputs" \
  --output table

echo ""
echo "Next steps:"
echo "  1. Copy the ApiUrl above"
echo "  2. Set it in frontend/.env.local: NEXT_PUBLIC_API_BASE_URL=<ApiUrl>"
echo "  3. Redeploy frontend or run: cd frontend && npm run dev"
