"""Chat window GUI with integrated message server."""
from __future__ import annotations

import os
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
sys.path.append(str(Path(__file__).resolve().parents[2]))

import tkinter as tk
from tkinter import scrolledtext
from tkinter import font
import threading
import time
from typing import Optional

from flask import Flask, request, jsonify

from config.communcation_settings import (
    MESSENGER_PORT,
    HOSTNAME,
    RESPONSE_STATUS_CODE_SUCCESS,
    RESPONSE_STATUS_CODE_ERROR,
)

# ====== Flask Server ======
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
    """Endpoint to clear all messages.

    Response JSON format:
        {"status": "success"}
    """
    clear_messages()
    return jsonify({"status": "success"}), RESPONSE_STATUS_CODE_SUCCESS


@flask_app.route('/health', methods=['GET'])
def health_check():
    """Endpoint for health check.

    Response JSON format:
        {"status": "ok"}
    """
    return jsonify({"status": "ok"}), RESPONSE_STATUS_CODE_SUCCESS


# ====== GUI ======
class ChatWindow:
    """Chat window GUI that displays messages from the internal message store."""

    def __init__(self, root: tk.Tk, poll_interval: float = 0.5):
        """Initialize ChatWindow.

        Args:
            root: Tkinter root window.
            poll_interval: Interval to poll for new messages (seconds).
        """
        self.root = root
        self.poll_interval = poll_interval
        root.title("Chat Window")

        # 日本語フォントを指定
        jp_font = font.Font(family="Meiryo", size=10)

        # 履歴表示スペース（スクロールテキスト）
        self.history = scrolledtext.ScrolledText(
            root, state='disabled', height=20, width=50, font=jp_font)
        self.history.grid(row=0, column=0, padx=10, pady=10)

        # Track last displayed message id
        self.last_id = 0

        # Start polling thread
        self.stop_event = threading.Event()
        self.fetch_thread = threading.Thread(
            target=self.fetch_loop, daemon=True)
        self.fetch_thread.start()

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def add_message(self, sender: str, text: str) -> None:
        """Add a message to the chat history display.

        Args:
            sender: Message sender name.
            text: Message text.
        """
        self.history.config(state='normal')
        self.history.insert(tk.END, f"{sender}: {text}\n")
        self.history.yview(tk.END)  # 自動スクロール
        self.history.config(state='disabled')

    def fetch_loop(self) -> None:
        """Poll for new messages and display them."""
        while not self.stop_event.is_set():
            try:
                new_messages = get_messages_since(self.last_id)
                for msg in new_messages:
                    msg_id = msg.get("id", 0)
                    if msg_id > self.last_id:
                        self.last_id = msg_id
                        sender = msg.get("sender", "")
                        text = msg.get("text", "")
                        self.root.after(0, self.add_message, sender, text)
            except Exception as e:
                print(f"Fetch Error: {e}")
            time.sleep(self.poll_interval)

    def on_close(self) -> None:
        """Handle window close event."""
        self.stop_event.set()
        self.root.destroy()


def run_flask_server(host: str, port: int) -> None:
    """Run Flask server in a separate thread.

    Args:
        host: Hostname to bind to.
        port: Port number to bind to.
    """
    # Suppress Flask startup messages
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    flask_app.run(host=host, port=port, debug=False, use_reloader=False)


def main(host: str = HOSTNAME, port: int = MESSENGER_PORT) -> None:
    """Main entry point to start chat window with integrated server.

    Args:
        host: Hostname for the server.
        port: Port number for the server.
    """
    # Start Flask server in a background thread
    server_thread = threading.Thread(
        target=run_flask_server,
        args=(host, port),
        daemon=True
    )
    server_thread.start()

    # Give server a moment to start
    time.sleep(0.5)

    # Start GUI
    root = tk.Tk()
    app_window = ChatWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
