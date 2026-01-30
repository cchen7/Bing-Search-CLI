from __future__ import annotations

import logging
from typing import Dict, List
import requests

from .config import Config

logger = logging.getLogger(__name__)


class BingSearchError(RuntimeError):
    pass


def search_web(query: str, config: Config, count: int = 5) -> List[Dict[str, str]]:
    if not config.bing_api_key:
        raise BingSearchError("Missing Bing API key. Set BING_API_KEY or /config bing_api_key.")

    headers = {"Ocp-Apim-Subscription-Key": config.bing_api_key}
    params = {
        "q": query,
        "count": count,
        "responseFilter": "Webpages",
        "textDecorations": False,
        "textFormat": "Raw",
        "safeSearch": "Moderate",
    }

    logger.debug("Bing search request: endpoint=%s params=%s", config.bing_endpoint, params)

    response = requests.get(config.bing_endpoint, headers=headers, params=params, timeout=15)
    if response.status_code >= 400:
        raise BingSearchError(f"Bing Search error {response.status_code}: {response.text}")

    payload = response.json()
    items = payload.get("webPages", {}).get("value", [])
    results: List[Dict[str, str]] = []
    for item in items:
        results.append(
            {
                "title": item.get("name", ""),
                "url": item.get("url", ""),
                "snippet": item.get("snippet", ""),
            }
        )

    logger.debug("Bing search returned %d results", len(results))
    return results
