#!/usr/bin/env bash
# RoadSense: create everything on Azure in one go. Paste into Azure Cloud Shell (Bash):
#   portal.azure.com -> the >_ icon at the top -> Bash
#
#   curl -fsSL https://raw.githubusercontent.com/NinadPandith/Road-Sense/claude/eloquent-gates-een41c/scripts/azure-setup.sh | bash
#
# It creates a resource group, a Container Apps environment and the "roadsense-api" app (with a
# placeholder image that the GitHub deploy workflow replaces), plus a managed identity that GitHub
# Actions signs in as (OIDC, no stored password). At the end it prints the values to paste into
# GitHub. Safe to run again.
set -euo pipefail

RG=roadsense
LOCATION=centralindia
ENV_NAME=roadsense-env
APP=roadsense-api

echo "==> Registering the Azure services Container Apps needs (first time takes a few minutes)"
az extension add --name containerapp --upgrade --only-show-errors >/dev/null
for ns in Microsoft.App Microsoft.OperationalInsights; do
  az provider register --namespace "$ns" --wait --only-show-errors >/dev/null
done

echo "==> Resource group $RG in $LOCATION"
az group create --name "$RG" --location "$LOCATION" --only-show-errors --output none

echo "==> Container Apps environment $ENV_NAME"
if ! az containerapp env show --name "$ENV_NAME" --resource-group "$RG" --output none 2>/dev/null; then
  az containerapp env create --name "$ENV_NAME" --resource-group "$RG" --location "$LOCATION" \
    --only-show-errors --output none
fi

echo "==> Container app $APP (placeholder image for now)"
if ! az containerapp show --name "$APP" --resource-group "$RG" --output none 2>/dev/null; then
  az containerapp create --name "$APP" --resource-group "$RG" --environment "$ENV_NAME" \
    --image mcr.microsoft.com/k8se/quickstart:latest --target-port 8000 --ingress external \
    --cpu 1 --memory 2Gi --min-replicas 0 --max-replicas 1 --only-show-errors --output none
fi
# The real API listens on 8000 (the placeholder uses 80; the deploy workflow swaps the image).
FQDN=$(az containerapp show --name "$APP" --resource-group "$RG" \
  --query properties.configuration.ingress.fqdn -o tsv)

echo "==> Deploy identity for GitHub (no password: GitHub signs in with OIDC)"
SUB=$(az account show --query id -o tsv)
TENANT=$(az account show --query tenantId -o tsv)
az identity create --name roadsense-deploy --resource-group "$RG" --only-show-errors --output none
CLIENT_ID=$(az identity show --name roadsense-deploy --resource-group "$RG" --query clientId -o tsv)
PRINCIPAL_ID=$(az identity show --name roadsense-deploy --resource-group "$RG" --query principalId -o tsv)
az role assignment create --assignee-object-id "$PRINCIPAL_ID" --assignee-principal-type ServicePrincipal \
  --role Contributor --scope "/subscriptions/$SUB/resourceGroups/$RG" --only-show-errors --output none 2>/dev/null \
  || echo "   (role already assigned)"
az identity federated-credential create --name github-production --identity-name roadsense-deploy \
  --resource-group "$RG" --issuer https://token.actions.githubusercontent.com \
  --subject "repo:NinadPandith/Road-Sense:environment:production" \
  --audiences api://AzureADTokenExchange --only-show-errors --output none 2>/dev/null \
  || echo "   (GitHub sign-in already set up)"

cat <<EOF

============================================================================================
Done. In GitHub: repository Settings -> Environments -> production -> add these VARIABLES
(they are IDs, not passwords):

  API_URL                  https://$FQDN
  AZURE_CLIENT_ID          $CLIENT_ID
  AZURE_TENANT_ID          $TENANT
  AZURE_SUBSCRIPTION_ID    $SUB
============================================================================================
EOF
