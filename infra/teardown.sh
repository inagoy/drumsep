#!/usr/bin/env bash
# Teardown script: delete the drumsep-api Cloud Run service only.

set -euo pipefail

PROJECT_ID="crowdstream-443823"
REGION="us-central1"
SERVICE_NAME="drumsep-api"

echo "WARNING: This will delete the Cloud Run service '${SERVICE_NAME}' in project ${PROJECT_ID}."
read -r -p "Are you sure? [y/N] " response
if [[ ! "$response" =~ ^[Yy]$ ]]; then
  echo "Aborted."
  exit 0
fi

gcloud run services delete "${SERVICE_NAME}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --quiet

echo "Cloud Run service '${SERVICE_NAME}' deleted."
