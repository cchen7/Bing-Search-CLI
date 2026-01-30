from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Iterator, Optional, Tuple, Dict, Tuple as Tup

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    PromptAgentDefinition,
    BingGroundingAgentTool,
    BingGroundingSearchToolParameters,
    BingGroundingSearchConfiguration,
)

from .config import Config

logger = logging.getLogger(__name__)


class GroundingError(RuntimeError):
    pass


@dataclass
class _GroundingSession:
    key: Tuple[str, str, str]
    client: AIProjectClient
    agent_name: str
    openai_client: Any


_SESSION: Optional[_GroundingSession] = None
_WARMUP_IN_FLIGHT = False


def _get_session(config: Config) -> _GroundingSession:
    return _get_session_with_trace(config)[0]


def _get_session_with_trace(config: Config) -> Tup[_GroundingSession, Dict[str, float]]:
    global _SESSION

    if not config.ai_project_endpoint:
        raise GroundingError("Missing AI project endpoint. Set AI_PROJECT_ENDPOINT or /config ai_project_endpoint.")
    if not config.ai_project_connection_id:
        raise GroundingError("Missing AI project connection ID. Set AI_PROJECT_CONNECTION_ID or /config ai_project_connection_id.")

    key = (
        config.ai_project_endpoint,
        config.ai_project_connection_id,
        config.ai_project_model_deployment,
    )

    if _SESSION and _SESSION.key == key:
        return _SESSION, {}

    logger.debug("Initializing AI Foundry grounding session")
    start_init = time.perf_counter()
    start_client = time.perf_counter()
    client = AIProjectClient(
        endpoint=config.ai_project_endpoint,
        credential=DefaultAzureCredential(),
    )
    client_ms = (time.perf_counter() - start_client) * 1000

    bing_tool = BingGroundingAgentTool(
        bing_grounding=BingGroundingSearchToolParameters(
            search_configurations=[
                BingGroundingSearchConfiguration(project_connection_id=config.ai_project_connection_id)
            ]
        )
    )

    instructions = (
        "You are a concise assistant. Use Bing grounding for current information. "
        "Always answer the user's query exactly. If it is unclear, ask for clarification. "
        "Return plain text with a short abstract and a 'Highlights' section using "
        "bullet points with citations. Answer in the same language as the query."
    )

    start_agent = time.perf_counter()
    agent = client.agents.create_version(
        agent_name="BingSearchCLI",
        definition=PromptAgentDefinition(
            model=config.ai_project_model_deployment,
            instructions=instructions,
            tools=[bing_tool],
        ),
    )
    agent_ms = (time.perf_counter() - start_agent) * 1000

    start_openai = time.perf_counter()
    openai_client = client.get_openai_client()
    openai_client_ms = (time.perf_counter() - start_openai) * 1000

    _SESSION = _GroundingSession(
        key=key,
        client=client,
        agent_name=agent.name,
        openai_client=openai_client,
    )
    init_ms = (time.perf_counter() - start_init) * 1000
    logger.debug("Grounding session initialized in %.1fms", init_ms)
    return _SESSION, {
        "session_init_ms": init_ms,
        "client_init_ms": client_ms,
        "agent_create_ms": agent_ms,
        "openai_client_init_ms": openai_client_ms,
    }


def grounding_answer(query: str, config: Config) -> tuple[str, Dict[str, float]]:
    session, init_trace = _get_session_with_trace(config)
    start_request = time.perf_counter()
    input_text = (
        "Answer the following question. Use grounding sources and cite them.\n"
        f"Question: {query}"
    )
    response = session.openai_client.responses.create(
        tool_choice="required",
        input=input_text,
        extra_body={"agent": {"name": session.agent_name, "type": "agent_reference"}},
    )
    request_ms = (time.perf_counter() - start_request) * 1000

    output = (getattr(response, "output_text", None) or "").strip()
    if _should_reject_answer(query, output):
        output = (
            "No relevant grounded sources were found for that query. "
            "Please refine the ticker or company name and try again."
        )
    trace = {"request_ms": request_ms}
    trace.update(init_trace)
    return output, trace


def grounding_stream(query: str, config: Config) -> tuple[Iterator[str], Dict[str, float]]:
    session, init_trace = _get_session_with_trace(config)
    start_request = time.perf_counter()
    input_text = (
        "Answer the following question. Use grounding sources and cite them.\n"
        f"Question: {query}"
    )
    try:
        stream = session.openai_client.responses.create(
            tool_choice="required",
            input=input_text,
            extra_body={"agent": {"name": session.agent_name, "type": "agent_reference"}},
            stream=True,
        )
    except TypeError:
        answer, trace = grounding_answer(query, config)
        trace.update(init_trace)
        return iter([answer]), trace

    trace: Dict[str, float] = {**init_trace}
    first_chunk_at: Optional[float] = None

    def iterator() -> Iterator[str]:
        nonlocal first_chunk_at
        for event in stream:
            text = _extract_stream_text(event)
            if text:
                if first_chunk_at is None:
                    first_chunk_at = time.perf_counter()
                    trace["first_chunk_ms"] = (first_chunk_at - start_request) * 1000
                yield text
        trace["request_ms"] = (time.perf_counter() - start_request) * 1000

    return iterator(), trace


def prewarm(config: Config) -> Dict[str, float]:
    _, trace = _get_session_with_trace(config)
    return trace


def warmup_request(config: Config) -> Dict[str, float]:
    global _WARMUP_IN_FLIGHT
    if _WARMUP_IN_FLIGHT:
        return {}
    _WARMUP_IN_FLIGHT = True
    session, init_trace = _get_session_with_trace(config)
    start_request = time.perf_counter()
    input_text = (config.warmup_prompt or "OK").strip() or "OK"
    try:
        response = session.openai_client.responses.create(
            tool_choice="auto",
            input=input_text,
            extra_body={"agent": {"name": session.agent_name, "type": "agent_reference"}},
        )
        _ = getattr(response, "output_text", None)
    except Exception:
        _WARMUP_IN_FLIGHT = False
        return {}
    request_ms = (time.perf_counter() - start_request) * 1000
    _WARMUP_IN_FLIGHT = False
    trace = {"request_ms": request_ms}
    trace.update(init_trace)
    return trace


def _extract_stream_text(event: Any) -> str:
    event_type = getattr(event, "type", None) or getattr(event, "event", None)
    if event_type in {"response.output_text.delta", "response.output_text"}:
        return getattr(event, "delta", None) or getattr(event, "text", None) or ""
    if isinstance(event, dict):
        if event.get("type") in {"response.output_text.delta", "response.output_text"}:
            return event.get("delta") or event.get("text") or ""
    return ""


def _should_reject_answer(query: str, answer: str) -> bool:
    tickers = re.findall(r"\$[A-Za-z]{1,6}", query)
    if not tickers:
        return False
    answer_upper = answer.upper()
    return all(ticker.replace("$", "") not in answer_upper for ticker in tickers)
