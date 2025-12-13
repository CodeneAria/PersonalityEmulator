#!/usr/bin/env python3
"""Send a KoboldCpp REST API request from a JSON file and print the response.

Default target:
  http://localhost:{KOBOLDCPP_PORT}/api/v1/generate

This script is intentionally dependency-free (uses stdlib urllib).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

from config.communcation_settings import KOBOLDCPP_PORT

# Edit these defaults directly when you want to change the target.
DEFAULT_HOST = "localhost"
DEFAULT_PORT = KOBOLDCPP_PORT
DEFAULT_ENDPOINT = "/api/v1/generate"

TEST_JSON_FILE_PATH = Path(__file__).resolve(
).parents[1] / "tests/KoboldCpp/input_format_example.json"


def _default_request_json_path() -> Path:
    """Return the default request JSON path.

    Uses a path relative to this repository so the script works even when
    executed from a different current working directory.
    """

    return TEST_JSON_FILE_PATH


def _extract_text(response_json: Any) -> Optional[str]:
    # KoboldAI/KoboldCpp style
    # {
    #   "results": [{"text": "...", ...}],
    #   ...
    # }
    if isinstance(response_json, dict):
        results = response_json.get("results")
        if isinstance(results, list) and results:
            first = results[0]
            if isinstance(first, dict) and isinstance(first.get("text"), str):
                return first["text"]

        # OpenAI Chat Completions style
        # {"choices": [{"message": {"content": "..."}}]}
        choices = response_json.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, dict):
                message = first.get("message")
                if isinstance(message, dict) and isinstance(message.get("content"), str):
                    return message["content"]
                # OpenAI Completions style
                if isinstance(first.get("text"), str):
                    return first["text"]

        # Some builds might return {"text": "..."}
        if isinstance(response_json.get("text"), str):
            return response_json["text"]

    return None


def _http_post_json(url: str, payload: Dict[str, Any], timeout_s: float) -> Any:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url=url,
        data=data,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            body = resp.read()
            charset = resp.headers.get_content_charset() or "utf-8"
            text = body.decode(charset, errors="replace")
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"raw": text}

    except urllib.error.HTTPError as e:
        body = None
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        raise RuntimeError(f"HTTP {e.code} {e.reason}: {body}") from e

    except urllib.error.URLError as e:
        raise RuntimeError(f"Connection error: {e}") from e


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=f"Send {TEST_JSON_FILE_PATH} to a running KoboldCpp via REST API and print its reply."
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
        # Backward-compatible fallback: allow running from repo root without absolute path.
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
        response_json = _http_post_json(url, payload, timeout_s=args.timeout)
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return 1

    extracted = _extract_text(response_json)
    if extracted is not None:
        print(extracted)
    else:
        # Fallback: print full JSON
        print(json.dumps(response_json, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
