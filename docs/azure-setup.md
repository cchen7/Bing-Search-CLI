# Azure Setup Guide

This guide covers how to provision Azure resources for Bing Search CLI.

## Authentication Methods

### API Key Authentication

Use an API key from **Resource Management > Keys and Endpoint** in the Azure Portal.

```python
client = AzureOpenAI(
    api_key="YOUR_API_KEY_HERE",
    azure_endpoint="https://your-resource.openai.azure.com/",
    api_version="2024-02-15-preview"
)
```

**Pros**: Simple, works anywhere.
**Cons**: Static secrets, manual rotation, no audit trail.

### RBAC Authentication (Microsoft Entra ID)

Assign **Cognitive Services OpenAI User** role in IAM and authenticate via `az login` locally or Managed Identity in Azure.

```python
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

token_provider = get_bearer_token_provider(
    DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
)

client = AzureOpenAI(
    azure_ad_token_provider=token_provider,
    azure_endpoint="https://your-resource.openai.azure.com/",
    api_version="2024-02-15-preview"
)
```

**Pros**: No secrets, auto-rotation, auditing.
**Cons**: More setup complexity.

---

## Option 1: Bing Web Search v7 + Azure OpenAI

This is the legacy approach using separate Bing Search and Azure OpenAI resources.

### Provision Resources

```bash
az login

RG=rg-bing-search-cli
LOCATION=eastus2
AOAI_NAME=<azure-openai-resource-name>
DEPLOYMENT_NAME=gpt-4o-mini

az group create -n $RG -l $LOCATION

# Create Azure OpenAI resource
az cognitiveservices account create \
  -g $RG -n $AOAI_NAME -l $LOCATION \
  --kind OpenAI --sku S0 --yes

# Get endpoint
az cognitiveservices account show -g $RG -n $AOAI_NAME --query properties.endpoint -o tsv

# Deploy model
az cognitiveservices account deployment create \
  -g $RG -n $AOAI_NAME \
  --deployment-name $DEPLOYMENT_NAME \
  --model-name gpt-4o-mini \
  --model-version 2024-07-18 \
  --model-format OpenAI
```

### Required Environment Variables

```bash
export BING_API_KEY="your-bing-api-key"
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
export AZURE_OPENAI_DEPLOYMENT="gpt-4o-mini"
# Optional: use API key instead of RBAC
export AZURE_OPENAI_API_KEY="your-openai-api-key"
```

---

## Option 2: Azure AI Foundry Grounding with Bing

This approach uses Azure AI Foundry's integrated Bing grounding capability.

### Provision Resources

```bash
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
RESOURCE_ID=$(az cognitiveservices account show -g $RG -n $AI_SERVICES_NAME --query id -o tsv)

az role assignment create \
  --assignee $USER_ID \
  --role "Cognitive Services OpenAI User" \
  --scope $RESOURCE_ID

# Get project endpoint
az rest --method GET \
  --url "${AI_SERVICES_ID}/projects/${PROJECT_NAME}?api-version=2025-04-01-preview" \
  --query "properties.endpoints.\"AI Foundry API\"" -o tsv
```

### Required Environment Variables

```bash
export SEARCH_PROVIDER="grounding"
export AI_PROJECT_ENDPOINT="https://<account>.services.ai.azure.com/api/projects/<project>"
export AI_PROJECT_CONNECTION_ID="/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<account>/projects/<project>/connections/bing-grounding"
export AI_PROJECT_MODEL_DEPLOYMENT="gpt-4o-mini"
```

---

## Troubleshooting

| Error | Solution |
|-------|----------|
| 401/403 errors | Check API key, RBAC role assignment, and endpoint URL |
| No results | Confirm Bing Search resource region and key |
| Azure OpenAI errors | Ensure deployment name matches config |
| Network timeouts | Retry and check corporate proxy settings |
