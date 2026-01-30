# Azure Setup Guide

This guide covers how to provision Azure AI Foundry resources for Bing Search CLI.

## Overview

Bing Search CLI uses Azure AI Foundry's Grounding with Bing capability. This requires:

1. A Bing Grounding resource (`Microsoft.Bing/accounts`)
2. An AI Services account with a deployed model
3. An AI Foundry project with a Bing connection

## Authentication

The CLI uses RBAC authentication via `DefaultAzureCredential`. Run `az login` locally or use Managed Identity in Azure.

Required role: **Cognitive Services OpenAI User** on the AI Services account.

## Provision Resources

```bash
# Variables
RG=rg-bing-grounding
LOCATION=eastus2
AI_SERVICES_NAME=<ai-services-name>
PROJECT_NAME=<project-name>
BING_NAME=<bing-grounding-name>
MODEL_DEPLOYMENT=gpt-4o-mini

# Register Bing provider
az provider register -n Microsoft.Bing --wait
az group create -n $RG -l $LOCATION

# Create Grounding with Bing resource
az resource create \
  --resource-group $RG \
  --resource-type "Microsoft.Bing/accounts" \
  --name $BING_NAME \
  --location global \
  --is-full-object \
  --properties '{
    "location": "global",
    "sku": {"name": "G1"},
    "kind": "Bing.Grounding"
  }'

# Create AI Services account with managed identity
az cognitiveservices account create \
  -g $RG -n $AI_SERVICES_NAME -l $LOCATION \
  --kind AIServices --sku S0 \
  --custom-domain $AI_SERVICES_NAME-$(date +%s) \
  --yes

az cognitiveservices account identity assign -g $RG -n $AI_SERVICES_NAME

# Deploy model
az cognitiveservices account deployment create \
  -g $RG -n $AI_SERVICES_NAME \
  --deployment-name $MODEL_DEPLOYMENT \
  --model-name gpt-4o-mini \
  --model-version 2024-07-18 \
  --model-format OpenAI \
  --sku-name GlobalStandard \
  --sku-capacity 10

# Create AI Foundry project
AI_SERVICES_ID=$(az cognitiveservices account show -g $RG -n $AI_SERVICES_NAME --query id -o tsv)

az rest --method PUT \
  --url "${AI_SERVICES_ID}/projects/${PROJECT_NAME}?api-version=2025-04-01-preview" \
  --body '{
    "location": "'$LOCATION'",
    "identity": {"type": "SystemAssigned"},
    "properties": {
      "displayName": "Bing Search CLI"
    }
  }'

# Create Bing connection on the project
BING_ID=$(az resource show -g $RG --resource-type "Microsoft.Bing/accounts" -n $BING_NAME --query id -o tsv)
BING_KEY=$(az rest --method post --url "${BING_ID}/listKeys?api-version=2020-06-10" --query key1 -o tsv)

az rest --method PUT \
  --url "${AI_SERVICES_ID}/projects/${PROJECT_NAME}/connections/bing-grounding?api-version=2025-04-01-preview" \
  --body "{
    \"properties\": {
      \"category\": \"ApiKey\",
      \"target\": \"https://api.bing.microsoft.com/\",
      \"authType\": \"ApiKey\",
      \"credentials\": {\"key\": \"${BING_KEY}\"},
      \"isSharedToAll\": true,
      \"metadata\": {
        \"ApiType\": \"Azure\",
        \"Location\": \"global\",
        \"ResourceId\": \"${BING_ID}\"
      }
    }
  }"

# Assign RBAC role
USER_ID=$(az ad signed-in-user show --query id -o tsv)
az role assignment create \
  --assignee $USER_ID \
  --role "Cognitive Services OpenAI User" \
  --scope $AI_SERVICES_ID

# Get project endpoint
az rest --method GET \
  --url "${AI_SERVICES_ID}/projects/${PROJECT_NAME}?api-version=2025-04-01-preview" \
  --query "properties.endpoints.\"AI Foundry API\"" -o tsv
```

## Get Configuration Values

After provisioning, get the values needed for environment variables:

```bash
# Project endpoint
AI_PROJECT_ENDPOINT=$(az rest --method GET \
  --url "${AI_SERVICES_ID}/projects/${PROJECT_NAME}?api-version=2025-04-01-preview" \
  --query "properties.endpoints.\"AI Foundry API\"" -o tsv)

# Connection ID
AI_PROJECT_CONNECTION_ID="${AI_SERVICES_ID}/projects/${PROJECT_NAME}/connections/bing-grounding"

echo "AI_PROJECT_ENDPOINT=${AI_PROJECT_ENDPOINT}"
echo "AI_PROJECT_CONNECTION_ID=${AI_PROJECT_CONNECTION_ID}"
echo "AI_PROJECT_MODEL_DEPLOYMENT=${MODEL_DEPLOYMENT}"
```

## Environment Variables

Set these in your shell or `.env` file:

```bash
export AI_PROJECT_ENDPOINT="https://<account>.services.ai.azure.com/api/projects/<project>"
export AI_PROJECT_CONNECTION_ID="/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<account>/projects/<project>/connections/bing-grounding"
export AI_PROJECT_MODEL_DEPLOYMENT="gpt-4o-mini"
```

## Troubleshooting

| Error | Solution |
|-------|----------|
| 401/403 errors | Wait for RBAC propagation (few minutes) or check role assignment |
| `Unsupported configuration` | Run `az cognitiveservices account identity assign` on the account |
| `404 Resource not found` | Use the **project** endpoint, not the account endpoint |
| `Invalid tool value: bing_grounding` | Connection must be on the **project**, not the account |

## Cleanup

To delete all resources:

```bash
az group delete -n $RG --yes --no-wait
```
