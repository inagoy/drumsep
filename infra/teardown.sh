#!/usr/bin/env bash
# Teardown script for drumsep web app infrastructure.
# Reverses the steps in infra/README.md.

set -euo pipefail

PROJECT_ID="crowdstream-443823"
REGION="us-central1"
BUCKET_NAME="crowdstream-drumsep"
SA_EMAIL="drumsep-api@${PROJECT_ID}.iam.gserviceaccount.com"
SERVICE_NAME="drumsep-api"
IMAGE="gcr.io/${PROJECT_ID}/drumsep-api"

echo "WARNING: This will delete all deployed resources for ${SERVICE_NAME} in project ${PROJECT_ID}."
read -r -p "Are you sure? [y/N] " response
if [[ ! "$response" =~ ^[Yy]$ ]]; then
  echo "Aborted."
  exit 0
fi

# 1. Delete Cloud Run service
echo "Deleting Cloud Run service ${SERVICE_NAME}..."
gcloud run services delete "${SERVICE_NAME}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --quiet

# 2. Delete GCS bucket (and all objects)
echo "Deleting bucket ${BUCKET_NAME}..."
gsutil -m rm -r "gs://${BUCKET_NAME}" || true

# 3. Delete container image tags/digests (ignore errors if none exist)
echo "Deleting container images ${IMAGE}..."
gcloud container images delete "${IMAGE}:latest" \
  --project="${PROJECT_ID}" \
  --quiet || true
gcloud container images delete "${IMAGE}" \
  --project="${PROJECT_ID}" \
  --quiet || true

# 4. Remove IAM self-impersonation binding, then delete service account
echo "Removing IAM bindings and deleting service account ${SA_EMAIL}..."
gcloud iam service-accounts remove-iam-policy-binding "${SA_EMAIL}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/iam.serviceAccountTokenCreator" \
  --project="${PROJECT_ID}" \
  --quiet || true

gcloud iam service-accounts delete "${SA_EMAIL}" \
  --project="${PROJECT_ID}" \
  --quiet || true

echo "Teardown complete."
