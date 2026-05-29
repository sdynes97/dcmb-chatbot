#!/usr/bin/env bash
# Run once before the first `terraform init` to create the remote state backend.
# Requires: az CLI logged in with Contributor on the subscription.
set -euo pipefail

SUBSCRIPTION_ID="${1:-$(az account show --query id -o tsv)}"
LOCATION="${2:-eastus}"

RG="dcmb-tfstate-rg"
SA="dcmbtfstate"
CONTAINER="tfstate"

echo "Bootstrapping Terraform state backend..."
echo "  Subscription: $SUBSCRIPTION_ID"
echo "  Location:     $LOCATION"

az group create --name "$RG" --location "$LOCATION" --output none
echo "  ✓ Resource group: $RG"

az storage account create \
  --name "$SA" \
  --resource-group "$RG" \
  --location "$LOCATION" \
  --sku Standard_LRS \
  --min-tls-version TLS1_2 \
  --allow-blob-public-access false \
  --output none
echo "  ✓ Storage account: $SA"

az storage container create \
  --name "$CONTAINER" \
  --account-name "$SA" \
  --auth-mode login \
  --output none
echo "  ✓ Container: $CONTAINER"

echo ""
echo "Backend ready. Now run:"
echo "  cd infra && terraform init"
