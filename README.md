# Bing Search CLI

Interactive command-line interface for Bing Search with AI summaries, powered by Azure AI Foundry Grounding.

## Features

- Interactive terminal prompt with slash commands
- AI-powered summaries with citations via Azure AI Foundry
- Streaming output support
- Local history storage in `~/.bing-search-cli`

## Prerequisites

- Python 3.10+
- Azure AI Foundry project with Bing Grounding connection (see [Azure Setup Guide](docs/azure-setup.md))

## Installation

### Option A: Local Installation (Isolated)

Install in a local directory with its own virtual environment. Recommended for trying out or development.

```bash
# Clone to local directory
git clone https://github.com/cchen7/Bing-Search-CLI.git
cd Bing-Search-CLI

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .
```

Run from the project directory:
```bash
source .venv/bin/activate
python -m bing_search_cli
```

### Option B: Global Installation

Install system-wide, available from anywhere.

```bash
pip install git+https://github.com/cchen7/Bing-Search-CLI.git
```

Run from anywhere:
```bash
bing-search-cli
```

## Quick Start

```bash
# Set credentials (required)
export AI_PROJECT_ENDPOINT="https://<account>.services.ai.azure.com/api/projects/<project>"
export AI_PROJECT_CONNECTION_ID="/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<account>/projects/<project>/connections/bing-grounding"

# Run interactive mode
bing-search-cli                    # Global install
python -m bing_search_cli          # Local install

# Or run a single query
bing-search-cli --query "What's the latest price of $NVDA"
```

## Configuration

Configure via environment variables or the `/config` command.

### Environment Variables

#### Required

| Variable | Description |
|----------|-------------|
| `AI_PROJECT_ENDPOINT` | Azure AI Foundry project endpoint URL |
| `AI_PROJECT_CONNECTION_ID` | Full resource ID of Bing grounding connection |

#### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `AI_PROJECT_MODEL_DEPLOYMENT` | `gpt-4o-mini` | Model deployment name |

#### Logging & Debug

| Variable | Default | Description |
|----------|---------|-------------|
| `BSC_LOG_LEVEL` | `INFO` | App log level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `BSC_SDK_LOG_LEVEL` | `ERROR` | Azure SDK log level |
| `BSC_TRACE` | `false` | Print timing breakdown for each query |

#### Performance Tuning

| Variable | Default | Description |
|----------|---------|-------------|
| `BSC_PREWARM` | `true` | Pre-initialize session on startup |
| `BSC_STREAM` | `true` | Stream output for queries |
| `BSC_WARMUP` | `true` | Run warmup request to reduce first-query latency |
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
| 401/403 errors | Check RBAC role assignment (`Cognitive Services OpenAI User`) |
| Connection errors | Verify `AI_PROJECT_ENDPOINT` and `AI_PROJECT_CONNECTION_ID` |
| Model errors | Ensure deployment name matches `AI_PROJECT_MODEL_DEPLOYMENT` |
| Slow first query | Enable `BSC_PREWARM=true` and `BSC_WARMUP=true` |

## License

Apache-2.0. See [LICENSE](LICENSE).
