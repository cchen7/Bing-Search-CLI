from __future__ import annotations

import logging
from typing import Dict, List

from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

from .config import Config

logger = logging.getLogger(__name__)


class SummaryError(RuntimeError):
    pass


def _detect_language_hint(text: str) -> str:
    for ch in text:
        if "\u4e00" <= ch <= "\u9fff":
            return "Use Simplified Chinese for the response."
    return "Use the same language as the user's query."


def _build_client(config: Config) -> AzureOpenAI:
    if not config.azure_openai_endpoint:
        raise SummaryError("Missing Azure OpenAI endpoint. Set AZURE_OPENAI_ENDPOINT or /config azure_openai_endpoint.")

    if config.azure_openai_api_key:
        logger.debug("Using Azure OpenAI API key authentication")
        return AzureOpenAI(
            api_key=config.azure_openai_api_key,
            azure_endpoint=config.azure_openai_endpoint,
            api_version=config.azure_openai_api_version,
        )

    logger.debug("Using Azure OpenAI RBAC authentication (DefaultAzureCredential)")
    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
    )
    return AzureOpenAI(
        azure_ad_token_provider=token_provider,
        azure_endpoint=config.azure_openai_endpoint,
        api_version=config.azure_openai_api_version,
    )


def summarize(query: str, results: List[Dict[str, str]], config: Config) -> str:
    if not results:
        return "No results found."

    client = _build_client(config)

    sources = []
    for i, item in enumerate(results, start=1):
        sources.append(
            f"[{i}] {item.get('title', '')}\nURL: {item.get('url', '')}\nSnippet: {item.get('snippet', '')}"
        )

    language_hint = _detect_language_hint(query)
    system_prompt = (
        "You are a concise assistant. Use only the provided sources. "
        "Return plain text with a short abstract and a 'Highlights' section "
        "using bullet points with citations. "
        + language_hint
    )
    user_prompt = (
        f"Query: {query}\n\nSources:\n" + "\n\n".join(sources) +
        "\n\nInstructions:\n"
        "1) Provide a short abstract (1-3 sentences).\n"
        "2) Add a header line: Highlights\n"
        "3) Provide bullet highlights (3-6 bullets).\n"
        "4) Add citations like [1] or [1][2] at the end of sentences/bullets.\n"
        "5) Use plain text only."
    )

    logger.debug("Azure OpenAI request: deployment=%s", config.azure_openai_deployment)

    response = client.chat.completions.create(
        model=config.azure_openai_deployment,
        temperature=0.2,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    content = response.choices[0].message.content
    return (content or "").strip()
