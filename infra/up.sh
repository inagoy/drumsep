#!/usr/bin/env bash
# Redeploy / bring up the drumsep-api Cloud Run service.
# Run after infra/teardown.sh or whenever you want to update the deployment.

set -euo pipefail

PROJECT_ID="crowdstream-443823"
REGION="us-central1"
BUCKET_NAME="crowdstream-drumsep"
SA_EMAIL="drumsep-api@${PROJECT_ID}.iam.gserviceaccount.com"
GH_PAGES_ORIGIN="https://docker-audio-tools.github.io"
SERVICE_NAME="drumsep-api"

echo "Building and deploying ${SERVICE_NAME}..."

gcloud builds submit \
  --config api/cloudbuild.yaml . \
  --project="${PROJECT_ID}"

gcloud run deploy "${SERVICE_NAME}" \
  --image "gcr.io/${PROJECT_ID}/drumsep-api:latest" \
  --region "${REGION}" \
  --service-account "${SA_EMAIL}" \
  --set-env-vars BUCKET_NAME="${BUCKET_NAME}",ALLOWED_ORIGIN="${GH_PAGES_ORIGIN}",RUNTIME_SERVICE_ACCOUNT="${SA_EMAIL}" \
  --memory 8Gi --cpu 4 \
  --timeout 900 \
  --concurrency 1 \
  --min-instances 0 \
  --allow-unauthenticated \
  --project="${PROJECT_ID}"

echo "Service deployed."
