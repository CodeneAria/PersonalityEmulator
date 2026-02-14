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

from source.messenger.message_source import MessageSource, normalize_source

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
# Voice input state
voice_input_active = False
voice_input_lock = threading.Lock()


def add_message_to_store(sender: str, text: str, source: str | MessageSource = MessageSource.SYSTEM.value) -> dict:
    """Add a message to the store and return the new message.

    Args:
        sender: Message sender name.
        text: Message text.
        source: Message source.
    """
    global next_id
    # Normalize source to a canonical string and restrict to allowed values
    source_str = normalize_source(source)

    with messages_lock:
        new_message = {"id": next_id, "sender": sender,
                       "text": text, "source": source_str}
        messages.append(new_message)
        next_id += 1
        return new_message


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


def update_message_in_store(message_id: int, new_text: str) -> dict | None:
    """Update a message's text by its ID.

    Args:
        message_id: The ID of the message to update.
        new_text: The new text content.

    Returns:
        The updated message dict, or None if not found.
    """
    with messages_lock:
        for msg in messages:
            if msg["id"] == message_id:
                msg["text"] = new_text
                return msg.copy()
        return None


def set_voice_input_state(active: bool) -> dict:
    """Set the voice input active state and return the current state."""
    global voice_input_active
    with voice_input_lock:
        voice_input_active = bool(active)
        return {"active": voice_input_active}


def get_voice_input_state() -> dict:
    """Return current voice input active state."""
    with voice_input_lock:
        return {"active": voice_input_active}


@flask_app.route("/")
def index():
    # Serve the web UI from the `gui` folder next to this file
    return send_from_directory("gui", "chat_window.html")


@flask_app.route('/messages', methods=['GET'])
def get_messages():
    """Endpoint to get all messages.

    Response JSON format:
        [{"id": int, "sender": str, "text": str, "source": str}, ...]
    """
    return jsonify(get_messages_from_store()), RESPONSE_STATUS_CODE_SUCCESS


@flask_app.route('/messages', methods=['POST'])
def post_message():
    """Endpoint to post a new message.

    Request JSON format:
        {"sender": str, "text": str, "source": str (optional)}

    Response JSON format:
        {"id": int, "sender": str, "text": str, "source": str}
    """
    try:
        data = request.get_json() or {}
        sender = data.get('sender', '')
        text = data.get('text', '')
        source = data.get('source', 'system')
        new_message = add_message_to_store(sender, text, source)
        return jsonify(new_message), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), RESPONSE_STATUS_CODE_ERROR


@flask_app.route('/messages/clear', methods=['POST'])
def clear_messages_endpoint():
    """Endpoint to clear all messages."""
    clear_messages()
    return jsonify({"status": "success"}), RESPONSE_STATUS_CODE_SUCCESS


@flask_app.route('/messages/<int:message_id>', methods=['PATCH'])
def update_message(message_id: int):
    """Endpoint to update an existing message.

    Request JSON format:
        {"text": str}

    Response JSON format:
        {"id": int, "sender": str, "text": str}
    """
    try:
        data = request.get_json() or {}
        new_text = data.get('text', '')
        updated_msg = update_message_in_store(message_id, new_text)
        if updated_msg is None:
            return jsonify({"status": "error", "message": "Message not found"}), 404
        return jsonify(updated_msg), RESPONSE_STATUS_CODE_SUCCESS
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), RESPONSE_STATUS_CODE_ERROR


@flask_app.route('/health', methods=['GET'])
def health_check():
    """Endpoint for health check."""
    return jsonify({"status": "ok"}), RESPONSE_STATUS_CODE_SUCCESS


@flask_app.route('/voice_input_state', methods=['GET'])
def voice_input_state_get():
    """Return the voice input active state."""
    return jsonify(get_voice_input_state()), RESPONSE_STATUS_CODE_SUCCESS


@flask_app.route('/voice_input_state', methods=['POST'])
def voice_input_state_post():
    """Set the voice input active state.

    Request JSON: {"active": bool}
    Response JSON: {"active": bool}
    """
    try:
        data = request.get_json() or {}
        active = bool(data.get('active', False))
        new_state = set_voice_input_state(active)
        return jsonify(new_state), RESPONSE_STATUS_CODE_SUCCESS
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), RESPONSE_STATUS_CODE_ERROR


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
