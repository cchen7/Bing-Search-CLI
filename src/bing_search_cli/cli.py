from __future__ import annotations

import argparse
import logging
import re
import shlex
import threading
import time as _time
from datetime import datetime
import time
from pathlib import Path
import shutil
from typing import Dict, List, Optional

from .config import Config, format_config, load_config, save_config, update_config
from .storage import append_history, load_history, now_iso
from .grounding import GroundingError, grounding_answer

BANNER = (
    "╭────────────────────────────────────────────────╮\n"
    "│ Bing Search CLI                                │\n"
    "│ Interactive search with real-time AI summaries │\n"
    "│                                                │\n"
    "│ Model: {model:<33}│\n"
    "│ Type /help for available commands              │\n"
    "╰────────────────────────────────────────────────╯"
)


def setup_logging(level: str, sdk_level: str) -> None:
    resolved_level = getattr(logging, level.upper(), logging.INFO)
    resolved_sdk_level = getattr(logging, sdk_level.upper(), logging.ERROR)
    logging.basicConfig(
        level=resolved_level,
        format="[%(levelname)s] %(name)s: %(message)s",
    )

    noisy = [
        "azure",
        "azure.core",
        "azure.identity",
        "azure.ai",
        "httpx",
        "httpcore",
        "openai",
        "urllib3",
    ]
    for name in noisy:
        logging.getLogger(name).setLevel(resolved_sdk_level)


def print_banner(config: Config) -> None:
    model_label = config.ai_project_model_deployment or "unknown"
    print(BANNER.format(model=model_label))


def print_help() -> None:
    print(
        "Commands:\n"
        "  /help                 Show this message\n"
        "  /exit                 Quit\n"
        "  /config               Show current config\n"
        "  /config key=value     Set config value\n"
        "  /config set key value Set config value\n"
        "  /config interactive   Prompt for config values\n"
        "  /save [filename]      Save the last answer to a file\n"
        "  /history [N]          Show last N queries"
    )


def parse_config_assignment(token: str) -> Optional[Dict[str, str]]:
    if "=" not in token:
        return None
    key, value = token.split("=", 1)
    key = key.strip()
    value = value.strip()
    if not key:
        return None
    return {key: value}


def prompt_config_interactive(config: Config) -> Config:
    print("Enter values (leave blank to keep current):")
    updates: Dict[str, str] = {}
    for field in [
        "ai_project_endpoint",
        "ai_project_connection_id",
        "ai_project_model_deployment",
        "log_level",
        "sdk_log_level",
        "prewarm_enabled",
        "streaming_enabled",
    ]:
        current = getattr(config, field)
        prompt = f"{field} [{current or ''}]: "
        value = input(prompt).strip()
        if value:
            updates[field] = value
    return update_config(config, updates)


def handle_config_command(config: Config, args: List[str]) -> Config:
    if not args:
        print(format_config(config))
        return config

    if args[0] == "interactive":
        return prompt_config_interactive(config)

    if args[0] == "set" and len(args) >= 3:
        key = args[1]
        value = " ".join(args[2:])
        return update_config(config, {key: value})

    assignment = parse_config_assignment(args[0])
    if assignment:
        return update_config(config, assignment)

    print("Invalid /config command. Type /help for usage.")
    return config


def save_last_answer(last_answer: str, filename: Optional[str]) -> None:
    if not last_answer:
        print("No answer to save yet.")
        return

    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"bing-search-{timestamp}.txt"

    path = Path.cwd() / filename
    path.write_text(last_answer, encoding="utf-8")
    print(f"Saved to {path}")


def show_history(limit: int) -> None:
    entries = load_history(limit=limit)
    if not entries:
        print("No history found.")
        return

    for entry in entries:
        timestamp = entry.get("timestamp", "")
        query = entry.get("query", "")
        print(f"{timestamp}  {query}")


def run_query(query: str, config: Config) -> str:
    start_total = time.perf_counter()
    answer, trace_info = grounding_answer(query, config)
    answer = _guard_ticker_answer(query, answer)
    append_history(
        {
            "timestamp": now_iso(),
            "query": query,
            "answer": answer,
        }
    )
    if config.trace_enabled and trace_info:
        total_ms = (time.perf_counter() - start_total) * 1000
        _print_trace({**trace_info, "total_ms": total_ms})
    return answer


def _print_status(message: str) -> None:
    print(message, flush=True)


def _guard_ticker_answer(query: str, answer: str) -> str:
    tickers = re.findall(r"\$[A-Za-z]{1,6}", query)
    if not tickers:
        return answer
    answer_upper = answer.upper()
    if all(ticker.replace("$", "") not in answer_upper for ticker in tickers):
        return (
            "No relevant grounded sources were found for that ticker. "
            "Please verify the ticker or include the company name and try again."
        )
    return answer


def _has_ticker(query: str) -> bool:
    return bool(re.findall(r"\$[A-Za-z]{1,6}", query))


def _print_trace(metrics: Dict[str, float]) -> None:
    ordered = [
        "warmup",
        "session_init_ms",
        "client_init_ms",
        "agent_create_ms",
        "openai_client_init_ms",
        "first_chunk_ms",
        "request_ms",
        "total_ms",
    ]
    parts = []
    for key in ordered:
        if key in metrics:
            parts.append(f"{key}={metrics[key]:.1f}ms")
    if parts:
        print("[trace] " + "  ".join(parts))


def _wrap_text(text: str, width: int) -> str:
    lines: List[str] = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line:
            lines.append("")
            continue

        prefix = ""
        content = line
        if line.startswith("• "):
            prefix = "• "
            content = line[2:].strip()
        elif line.startswith("- "):
            prefix = "• "
            content = line[2:].strip()
        elif line.startswith("* "):
            prefix = "• "
            content = line[2:].strip()

        words = content.split()
        if not words:
            lines.append(prefix.rstrip())
            continue

        current = prefix + words[0]
        for word in words[1:]:
            if len(current) + 1 + len(word) <= width:
                current += " " + word
            else:
                lines.append(current)
                current = (prefix + word).strip()
        lines.append(current)

    return "\n".join(lines)


def format_answer(answer: str) -> str:
    if not answer:
        return ""
    width = shutil.get_terminal_size((100, 20)).columns
    width = max(60, min(width, 120))

    lines = answer.strip().splitlines()
    normalized_headers = []
    highlights_seen = False
    for line in lines:
        stripped = line.strip()
        lower = stripped.lower()
        if "highlight" in lower:
            if highlights_seen:
                continue
            highlights_seen = True
            normalized_headers.append("Highlights")
            continue
        normalized_headers.append(line)
    lines = normalized_headers
    bullet_index = None
    for idx, line in enumerate(lines):
        if line.lstrip().startswith(("- ", "* ", "• ")):
            bullet_index = idx
            break

    if bullet_index is not None:
        header_present = any(
            "highlight" in line.lower() for line in lines[:bullet_index]
        )
        if not header_present:
            lines.insert(bullet_index, "")
            lines.insert(bullet_index, "Highlights")

    normalized = []
    for line in lines:
        if line.lstrip().startswith(("- ", "* ")):
            normalized.append("• " + line.lstrip()[2:])
        else:
            normalized.append(line)

    return _wrap_text("\n".join(normalized), width)


def main() -> None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--query", "-q", help="Run a single query and exit")
    parser.add_argument("--help", action="store_true", help="Show help")
    args, _ = parser.parse_known_args()

    config = load_config()
    setup_logging(config.log_level, config.sdk_log_level)
    print_banner(config)

    def _background_warmup() -> None:
        try:
            from .grounding import prewarm, warmup_request

            if config.prewarm_enabled:
                trace = prewarm(config)
                if config.trace_enabled and trace:
                    _print_trace(trace)
            if config.warmup_enabled:
                if config.warmup_delay_ms > 0:
                    _time.sleep(config.warmup_delay_ms / 1000)
                trace = warmup_request(config)
                if config.trace_enabled and trace:
                    _print_trace({"warmup": 1, **trace})
        except Exception as exc:  # noqa: BLE001
            logging.getLogger(__name__).debug("Warmup failed: %s", exc)

    if config.prewarm_enabled or config.warmup_enabled:
        threading.Thread(target=_background_warmup, daemon=True).start()

    if args.help:
        print_help()
        return

    if args.query:
        try:
            start_total = time.perf_counter()
            if config.streaming_enabled and not _has_ticker(args.query):
                from .grounding import grounding_stream

                _print_status("Searching...")
                chunks, trace_info = grounding_stream(args.query, config)
                print("\n", end="")
                collected: List[str] = []
                first_byte_reported = False
                for chunk in chunks:
                    collected.append(chunk)
                    if config.trace_enabled and not first_byte_reported and "first_chunk_ms" in trace_info:
                        print(f"[ttfb] {trace_info['first_chunk_ms']:.1f}ms\n")
                        first_byte_reported = True
                    print(chunk, end="", flush=True)
                print("\n")
                answer = "".join(collected)
                if config.trace_enabled and trace_info:
                    total_ms = (time.perf_counter() - start_total) * 1000
                    _print_trace({**trace_info, "total_ms": total_ms})
            else:
                answer = run_query(args.query, config)
                print("\n" + format_answer(answer) + "\n")
        except GroundingError as exc:
            logging.getLogger(__name__).error("%s", exc)
        except Exception as exc:  # noqa: BLE001
            logger = logging.getLogger(__name__)
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception("Unexpected error")
            else:
                logger.error("Unexpected error: %s", exc)
        save_config(config)
        return

    last_answer = ""

    while True:
        try:
            line = input("❯ ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting...")
            break

        if not line:
            continue

        if line.startswith("/"):
            parts = shlex.split(line)
            command = parts[0]
            args_list = parts[1:]

            if command in ("/exit", "/quit"):
                print("Bye.")
                break
            if command == "/help":
                print_help()
                continue
            if command == "/config":
                config = handle_config_command(config, args_list)
                continue
            if command == "/save":
                filename = args_list[0] if args_list else None
                save_last_answer(last_answer, filename)
                continue
            if command == "/history":
                limit = int(args_list[0]) if args_list else 5
                show_history(limit)
                continue

            print("Unknown command. Type /help for usage.")
            continue

        try:
            start_total = time.perf_counter()
            if config.streaming_enabled and not _has_ticker(line):
                from .grounding import grounding_stream

                _print_status("Searching...")
                chunks, trace_info = grounding_stream(line, config)
                print("\n", end="")
                collected = []
                first_byte_reported = False
                for chunk in chunks:
                    collected.append(chunk)
                    if config.trace_enabled and not first_byte_reported and "first_chunk_ms" in trace_info:
                        print(f"[ttfb] {trace_info['first_chunk_ms']:.1f}ms\n")
                        first_byte_reported = True
                    print(chunk, end="", flush=True)
                print("\n")
                answer = "".join(collected)
                if config.trace_enabled and trace_info:
                    total_ms = (time.perf_counter() - start_total) * 1000
                    _print_trace({**trace_info, "total_ms": total_ms})
                last_answer = answer
            else:
                answer = run_query(line, config)
                print("\n" + format_answer(answer) + "\n")
                last_answer = answer
        except KeyboardInterrupt:
            print("\nCancelled.\n")
        except GroundingError as exc:
            logging.getLogger(__name__).error("%s", exc)
        except Exception as exc:  # noqa: BLE001
            logger = logging.getLogger(__name__)
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception("Unexpected error")
            else:
                logger.error("Unexpected error: %s", exc)

    save_config(config)
