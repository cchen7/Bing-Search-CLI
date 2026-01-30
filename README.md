# Bing Search CLI

Interactive command-line interface for Bing Web Search v7 with Azure OpenAI summaries. Designed for fast, repeatable searches with a clean terminal UX.

## Features
- Bannered interactive prompt.
- Slash commands for configuration and control.
- Bing Web Search v7 results with short abstract + bullet highlights + citations.
- Session history stored locally in ~/.bing-search-cli.
- `/save` exports the last answer to the current directory.
- Verbose logging for debugging.

## Prerequisites
- Python 3.10+.
- Azure CLI (for provisioning sample resources).
- Bing Web Search v7 resource.
- Azure OpenAI resource with a deployed model.

## Install
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Configuration
You can configure via environment variables or `/config`.

### Environment Variables
- `BING_API_KEY` (required)
- `BING_ENDPOINT` (default: https://api.bing.microsoft.com/v7.0/search)
- `AZURE_OPENAI_ENDPOINT` (required)
- `AZURE_OPENAI_API_VERSION` (set to the latest API version supported by your resource; example: 2024-02-15-preview)
- `AZURE_OPENAI_DEPLOYMENT` (default: gpt-4o-mini)
- `AZURE_OPENAI_API_KEY` (optional; required for key auth)
- `AI_PROJECT_ENDPOINT` (required for grounding provider)
- `AI_PROJECT_CONNECTION_ID` (required for grounding provider)
- `AI_PROJECT_MODEL_DEPLOYMENT` (default: gpt-4o-mini)
- `SEARCH_PROVIDER` (default: bing_web; options: bing_web, grounding)
- `BSC_LOG_LEVEL` (default: INFO; app logs)
- `BSC_SDK_LOG_LEVEL` (default: ERROR; SDK logs)
- `BSC_TRACE` (default: false; prints timing breakdown per query)
- `BSC_PREWARM` (default: true; pre-initialize grounding session)
- `BSC_STREAM` (default: true; stream output for grounding queries)
- `BSC_WARMUP` (default: true; run a lightweight warmup request on startup)
- `BSC_WARMUP_DELAY_MS` (default: 1200; delay warmup to avoid contention)
- `BSC_WARMUP_PROMPT` (default: OK; minimal warmup input)

### `/config` Command
- `/config` shows current config (secrets redacted).
- `/config key=value` sets a single value.
- `/config set key value` sets a single value.
- `/config interactive` prompts for values.

## Usage
```bash
bing-search-cli
```

Run a single query (non-interactive):
```bash
bing-search-cli --query "What's the latest price of $NVDA"
```

### Slash Commands
- `/help` show commands.
- `/exit` quit.
- `/config` set or view configuration.
- `/save [filename]` save the last answer (default: timestamped file).
- `/history [N]` show last N entries.

### Search Providers
- `bing_web`: Bing Web Search v7 + Azure OpenAI summarizer.
- `grounding`: Azure AI Foundry Grounding with Bing (recommended).

> Note: Microsoft has moved Bing Search into Azure AI Foundry Grounding. For new projects, prefer `grounding`.

### Example Output
```
╭────────────────────────────────────────────────╮
│ Bing Search CLI                                │
│ Interactive search with real-time AI summaries │
│                                                │
│ Model: gpt-4o-mini                             │
│ Type /help for available commands              │
╰────────────────────────────────────────────────╯
❯  what's the latest price of $NVDA

The latest NVIDIA (NVDA) stock price is $189.65, up 1.71% ($3.18) as of January 27, 2026, 11:59 AM EST[1].

Highlights
- Shares gained 52.40% over the past year; 52-week range $86.62–$212.19.[1][2]
- Analysts maintain “Strong Buy” consensus with a median target around $263.[2]
- Data center revenue drove record quarterly results in FY2026.[2][3]
```

## Azure OpenAI Authentication Guidance

### 1) Local Key Access (API Key Authentication)
Use an API key from **Resource Management > Keys and Endpoint** in the Azure Portal.

```python
client = AzureOpenAI(
    api_key="YOUR_API_KEY_HERE",
    azure_endpoint="https://your-resource.openai.azure.com/",
  api_version="2024-02-15-preview"
)
```

**Pros**: simple, works anywhere. **Cons**: static secrets, manual rotation, no audit trail.

### 2) RBAC Access (Microsoft Entra ID / Token Authentication)
Recommended for production. Assign **Cognitive Services OpenAI User** role in IAM and authenticate via `az login` locally or Managed Identity in Azure.

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

**Pros**: no secrets, auto-rotation, auditing. **Cons**: more setup complexity.

## Azure CLI: Sample Resource Provisioning (eastus2)

> Replace names in angle brackets and choose a model available in your region.

```bash
az login

RG=rg-bing-search-cli
LOCATION=eastus2
AOAI_NAME=<azure-openai-resource-name>
DEPLOYMENT_NAME=gpt-4o-mini

az group create -n $RG -l $LOCATION

# Azure OpenAI
az cognitiveservices account create \
  -g $RG -n $AOAI_NAME -l $LOCATION \
  --kind OpenAI --sku S0 --yes

az cognitiveservices account show -g $RG -n $AOAI_NAME --query properties.endpoint -o tsv

az cognitiveservices account deployment create \
  -g $RG -n $AOAI_NAME \
  --deployment-name $DEPLOYMENT_NAME \
  --model-name <MODEL_NAME> \
  --model-version <MODEL_VERSION> \
  --model-format OpenAI
```

### Grounding with Bing (AI Foundry) — Recommended

```bash
RG=rg-bing-grounding
LOCATION=eastus2
AI_SERVICES_NAME=<ai-services-name>
PROJECT_NAME=<project-name>
BING_NAME=<bing-grounding-name>
MODEL_DEPLOYMENT=<model-deployment>

az provider register -n Microsoft.Bing --wait
az group create -n $RG -l $LOCATION

# Grounding with Bing resource
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

# AI Services account + managed identity
az cognitiveservices account create \
  -g $RG -n $AI_SERVICES_NAME -l $LOCATION \
  --kind AIServices --sku S0 \
  --custom-domain $AI_SERVICES_NAME-$(date +%s) \
  --yes

az cognitiveservices account identity assign -g $RG -n $AI_SERVICES_NAME

# Deploy a model
az cognitiveservices account deployment create \
  -g $RG -n $AI_SERVICES_NAME \
  --deployment-name $MODEL_DEPLOYMENT \
  --model-name <MODEL_NAME> \
  --model-version <MODEL_VERSION> \
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

# RBAC for AI Services
USER_ID=$(az ad signed-in-user show --query id -o tsv)
RESOURCE_ID=$(az cognitiveservices account show -g $RG -n $AI_SERVICES_NAME --query id -o tsv)

az role assignment create \
  --assignee $USER_ID \
  --role "Cognitive Services OpenAI User" \
  --scope $RESOURCE_ID

# Project endpoint for AI Foundry
az rest --method GET \
  --url "${AI_SERVICES_ID}/projects/${PROJECT_NAME}?api-version=2025-04-01-preview" \
  --query "properties.endpoints.\"AI Foundry API\"" -o tsv
```

## Troubleshooting
- **401/403 errors**: check API key, RBAC role assignment, and endpoint URL.
- **No results**: confirm Bing Search resource region and key.
- **Azure OpenAI errors**: ensure deployment name matches `AZURE_OPENAI_DEPLOYMENT`.
- **Network timeouts**: retry and check corporate proxy settings.

### Debug & Trace
Use these switches to diagnose performance and logging issues:

- `BSC_LOG_LEVEL=DEBUG` enables app debug logs.
- `BSC_SDK_LOG_LEVEL=DEBUG` enables Azure/OpenAI SDK logs.
- `BSC_TRACE=true` prints per-request timing breakdowns.
- `BSC_PREWARM=true` initializes the grounding session on startup.
- `BSC_WARMUP=true` runs a lightweight warmup request.
- `BSC_WARMUP_DELAY_MS=1200` delays warmup to avoid contention.
- `BSC_STREAM=true` streams output and prints `[ttfb]` when the first chunk arrives.

## Rate Limits
- Bing Search and Azure OpenAI both enforce rate limits by tier.
- If you hit 429s, reduce query frequency and implement backoff.

## License
Apache-2.0. See LICENSE.
