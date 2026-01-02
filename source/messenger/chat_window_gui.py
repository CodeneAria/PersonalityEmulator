"""Flask server for chat window (serves web-based UI).

This module provides the in-memory message store and HTTP
endpoints used by the web UI located in `source/messenger/gui/chat_window.html`.
"""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
sys.path.append(str(Path(__file__).resolve().parents[2]))

import threading
from pathlib import Path
import logging

from flask import Flask, request, jsonify, send_from_directory

from config.communcation_settings import (
    MESSENGER_PORT,
    HOSTNAME,
    RESPONSE_STATUS_CODE_SUCCESS,
    RESPONSE_STATUS_CODE_ERROR,
)

# Flask app
flask_app = Flask(__name__)

# In-memory message store
messages: list[dict] = []
next_id = 1
messages_lock = threading.Lock()


def add_message_to_store(sender: str, text: str) -> dict:
    """Add a message to the store and return the new message."""
    global next_id
    with messages_lock:
        new_msg = {"id": next_id, "sender": sender, "text": text}
        messages.append(new_msg)
        next_id += 1
        return new_msg


def get_messages_from_store() -> list[dict]:
    """Get all messages from the store."""
    with messages_lock:
        return messages.copy()


def get_messages_since(last_id: int) -> list[dict]:
    """Get messages with id greater than last_id."""
    with messages_lock:
        return [msg for msg in messages if msg["id"] > last_id]


def clear_messages() -> None:
    """Clear all messages from the store."""
    global next_id
    with messages_lock:
        messages.clear()
        next_id = 1


@flask_app.route("/")
def index():
    # Serve the web UI from the `gui` folder next to this file
    return send_from_directory("gui", "chat_window.html")


@flask_app.route('/messages', methods=['GET'])
def get_messages():
    """Endpoint to get all messages.

    Response JSON format:
        [{"id": int, "sender": str, "text": str}, ...]
    """
    return jsonify(get_messages_from_store()), RESPONSE_STATUS_CODE_SUCCESS


@flask_app.route('/messages', methods=['POST'])
def post_message():
    """Endpoint to post a new message.

    Request JSON format:
        {"sender": str, "text": str}

    Response JSON format:
        {"id": int, "sender": str, "text": str}
    """
    try:
        data = request.get_json() or {}
        sender = data.get('sender', '')
        text = data.get('text', '')
        new_msg = add_message_to_store(sender, text)
        return jsonify(new_msg), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), RESPONSE_STATUS_CODE_ERROR


@flask_app.route('/messages/clear', methods=['POST'])
def clear_messages_endpoint():
    """Endpoint to clear all messages."""
    clear_messages()
    return jsonify({"status": "success"}), RESPONSE_STATUS_CODE_SUCCESS


@flask_app.route('/health', methods=['GET'])
def health_check():
    """Endpoint for health check."""
    return jsonify({"status": "ok"}), RESPONSE_STATUS_CODE_SUCCESS


def run_flask_server(host: str, port: int) -> None:
    """Run Flask server (blocking).

    Args:
        host: Hostname to bind to.
        port: Port number to bind to.
    """
    # Suppress werkzeug info messages unless warnings/errors occur
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    # Run server (blocking); choose production server separately if needed
    flask_app.run(host=host, port=port, debug=False, use_reloader=False)


def main(host: str = HOSTNAME, port: int = MESSENGER_PORT) -> None:
    """Start the Flask server that serves the web chat UI."""
    run_flask_server(host, port)


if __name__ == "__main__":
    main()
