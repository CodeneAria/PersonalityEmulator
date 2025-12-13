#!/usr/bin/env python3
"""Send a KoboldCpp SSE streaming request from a JSON file and print tokens.

This mirrors tests/test_koboldcpp_request.py but uses SSE streaming
via `requests` + `sseclient` to receive incremental events.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import argparse
import json
import sys
from typing import Any, Dict, Optional

import requests
from sseclient import SSEClient

from config.communcation_settings import KOBOLDCPP_PORT

# Edit these defaults directly when you want to change the target.
DEFAULT_HOST = "localhost"
DEFAULT_PORT = KOBOLDCPP_PORT
DEFAULT_ENDPOINT = "/api/extra/generate/stream"

TEST_JSON_FILE_PATH = Path(__file__).resolve(
).parents[1] / "tests/KoboldCpp/input_format_example.json"


def _default_request_json_path() -> Path:
    return TEST_JSON_FILE_PATH


def _extract_text(response_json: Any) -> Optional[str]:
    # Reuse same extraction heuristics as request script
    if isinstance(response_json, dict):
        token = response_json.get("token")
        if isinstance(token, str):
            return token

    if isinstance(response_json, dict):
        results = response_json.get("results")
        if isinstance(results, list) and results:
            first = results[0]
            if isinstance(first, dict) and isinstance(first.get("text"), str):
                return first["text"]

        choices = response_json.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, dict):
                message = first.get("message")
                if isinstance(message, dict) and isinstance(message.get("content"), str):
                    return message["content"]
                if isinstance(first.get("text"), str):
                    return first["text"]

        if isinstance(response_json.get("text"), str):
            return response_json["text"]

    return None


def _sse_post_stream(url: str, payload: Dict[str, Any], timeout_s: float):
    """Post JSON and yield SSE events (strings).

    Raises RuntimeError on non-2xx or connection errors.
    """
    headers = {
        "Accept": "text/event-stream",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(url, json=payload, headers=headers,
                             stream=True, timeout=timeout_s)
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Connection error: {e}") from e

    if resp.status_code < 200 or resp.status_code >= 300:
        # Try to capture body for diagnostics
        body = None
        try:
            body = resp.text
        except Exception:
            body = ""
        raise RuntimeError(f"HTTP {resp.status_code} {resp.reason}: {body}")

    # Wrap with SSEClient to parse server-sent events
    client = SSEClient(resp)

    for event in client.events():
        yield event.data


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=f"Send {TEST_JSON_FILE_PATH} to a running KoboldCpp via SSE and print streamed tokens."
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=f"KoboldCpp host (default: {DEFAULT_HOST})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"KoboldCpp port (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--endpoint",
        default=DEFAULT_ENDPOINT,
        help=f"API endpoint path (default: {DEFAULT_ENDPOINT})",
    )
    parser.add_argument(
        "--json",
        dest="json_path",
        default=str(_default_request_json_path()),
        help=f"Path to request JSON file (default: repo-relative {TEST_JSON_FILE_PATH})",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=180.0,
        help="Request timeout seconds (default: 180)",
    )
    args = parser.parse_args(argv)

    json_path = Path(args.json_path).expanduser()
    if not json_path.exists():
        fallback = TEST_JSON_FILE_PATH
        if fallback.exists():
            json_path = fallback
        else:
            print(f"JSON file not found: {json_path}", file=sys.stderr)
            return 2

    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Failed to read/parse JSON: {json_path}: {e}", file=sys.stderr)
        return 2

    if not isinstance(payload, dict):
        print("JSON root must be an object (dict).", file=sys.stderr)
        return 2

    base_url = f"http://{args.host}:{args.port}"
    url = base_url + \
        (args.endpoint if args.endpoint.startswith("/") else "/" + args.endpoint)

    try:
        print("Connecting for SSE stream...")
        first = True
        for data in _sse_post_stream(url, payload, timeout_s=args.timeout):
            if not data:
                continue
            # Some SSE servers may send simple text; try parse as JSON
            if data.strip() == "[DONE]":
                break

            try:
                parsed = json.loads(data)
            except Exception:
                parsed = None

            if isinstance(parsed, (dict, list)):

                text = None
                if isinstance(parsed, dict):
                    text = _extract_text(parsed)
                if text is not None:
                    # Print without newline to stream tokens continuously
                    print(text, end="", flush=True)
                else:
                    print(json.dumps(parsed, ensure_ascii=False), flush=True)
            else:
                # Plain text event
                print(data, end=("" if first else ""), flush=True)
            first = False

        print("\nStream closed!")

    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
