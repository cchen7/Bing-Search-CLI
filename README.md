# Bing Search CLI

Interactive command-line interface for Bing Web Search with Azure OpenAI summaries.

## Features

- Interactive terminal prompt with slash commands
- Two search providers: Bing Web Search v7 or Azure AI Foundry Grounding
- AI-powered summaries with citations
- Local history storage in `~/.bing-search-cli`
- Streaming output support

## Prerequisites

- Python 3.10+
- Azure resources (see [Azure Setup Guide](docs/azure-setup.md))

## Installation

```bash
pip install git+https://github.com/cchen7/Bing-Search-CLI.git
```

Or install from source:

```bash
git clone https://github.com/cchen7/Bing-Search-CLI.git
cd Bing-Search-CLI
pip install -e .
```

## Quick Start

```bash
# Set credentials (see Configuration for details)
export SEARCH_PROVIDER="grounding"
export AI_PROJECT_ENDPOINT="https://..."
export AI_PROJECT_CONNECTION_ID="/subscriptions/..."

# Run interactive mode
bing-search-cli

# Or run a single query
bing-search-cli --query "What's the latest price of $NVDA"
```

## Configuration

Configure via environment variables or the `/config` command.

### Search Providers

| Provider | Description |
|----------|-------------|
| `bing_web` | Bing Web Search v7 + Azure OpenAI summarizer |
| `grounding` | Azure AI Foundry Grounding with Bing |

Set provider: `export SEARCH_PROVIDER="grounding"`

### Environment Variables

#### Core Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SEARCH_PROVIDER` | No | `bing_web` | Search provider: `bing_web` or `grounding` |

#### Bing Web Search Provider (`bing_web`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BING_API_KEY` | Yes | - | API key from Bing Search resource |
| `BING_ENDPOINT` | No | `https://api.bing.microsoft.com/v7.0/search` | Bing Search API endpoint |
| `AZURE_OPENAI_ENDPOINT` | Yes | - | Azure OpenAI resource endpoint |
| `AZURE_OPENAI_DEPLOYMENT` | No | `gpt-4o-mini` | Model deployment name |
| `AZURE_OPENAI_API_VERSION` | No | `2024-02-15-preview` | API version |
| `AZURE_OPENAI_API_KEY` | No | - | API key (if not using RBAC auth) |

#### AI Foundry Grounding Provider (`grounding`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AI_PROJECT_ENDPOINT` | Yes | - | AI Foundry project endpoint URL |
| `AI_PROJECT_CONNECTION_ID` | Yes | - | Full resource ID of Bing connection |
| `AI_PROJECT_MODEL_DEPLOYMENT` | No | `gpt-4o-mini` | Model deployment name |

#### Logging & Debug

| Variable | Default | Description |
|----------|---------|-------------|
| `BSC_LOG_LEVEL` | `INFO` | App log level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `BSC_SDK_LOG_LEVEL` | `ERROR` | Azure SDK log level |
| `BSC_TRACE` | `false` | Print timing breakdown for each query |

#### Performance Tuning

| Variable | Default | Description |
|----------|---------|-------------|
| `BSC_PREWARM` | `true` | Pre-initialize grounding session on startup |
| `BSC_STREAM` | `true` | Stream output for grounding queries |
| `BSC_WARMUP` | `true` | Run warmup request on startup to reduce first-query latency |
| `BSC_WARMUP_DELAY_MS` | `1200` | Delay (ms) before warmup request |
| `BSC_WARMUP_PROMPT` | `OK` | Prompt text for warmup request |

### `/config` Command

```bash
/config                      # Show current config (secrets redacted)
/config key=value            # Set a value
/config set key value        # Set a value (alternative syntax)
/config interactive          # Interactive configuration wizard
```

## Usage

### Slash Commands

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/exit` | Quit the application |
| `/config` | View or set configuration |
| `/save [filename]` | Save last answer to file |
| `/history [N]` | Show last N queries (default: 5) |

### Example Session

```
╭────────────────────────────────────────────────╮
│ Bing Search CLI                                │
│ Interactive search with real-time AI summaries │
│                                                │
│ Model: gpt-4o-mini                             │
│ Type /help for available commands              │
╰────────────────────────────────────────────────╯
❯ what's the latest price of $NVDA

The latest NVIDIA (NVDA) stock price is $189.65, up 1.71% ($3.18) as of January 27, 2026, 11:59 AM EST[1].

Highlights
• Shares gained 52.40% over the past year; 52-week range $86.62–$212.19.[1][2]
• Analysts maintain "Strong Buy" consensus with a median target around $263.[2]
• Data center revenue drove record quarterly results in FY2026.[2][3]
```

## Azure Setup

See [Azure Setup Guide](docs/azure-setup.md) for detailed instructions on provisioning Azure resources.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| 401/403 errors | Check API key or RBAC role assignment |
| No results | Verify Bing Search resource and API key |
| Model errors | Ensure deployment name matches `*_DEPLOYMENT` variable |
| Slow first query | Enable `BSC_PREWARM=true` and `BSC_WARMUP=true` |

## License

Apache-2.0. See [LICENSE](LICENSE).
