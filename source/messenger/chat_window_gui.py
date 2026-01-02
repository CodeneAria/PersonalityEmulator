"""Chat window GUI with integrated message server."""
from __future__ import annotations

import os
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
sys.path.append(str(Path(__file__).resolve().parents[2]))

import tkinter as tk
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

        # 履歴表示スペース（スクロール可能なフレーム）
        container = tk.Frame(root)
        container.grid(row=0, column=0, padx=10, pady=10, sticky='nsew')

        # Canvas + vertical scrollbar
        self.canvas = tk.Canvas(container, borderwidth=0, highlightthickness=0)
        vsb = tk.Scrollbar(container, orient='vertical',
                           command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side='right', fill='y')
        self.canvas.pack(side='left', fill='both', expand=True)

        # Frame inside canvas to hold message widgets
        self.messages_frame = tk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.messages_frame, anchor='nw')

        # Make the messages area expand with window
        root.grid_rowconfigure(0, weight=1)
        root.grid_columnconfigure(0, weight=1)

        # Bind configure events to update scrollregion and canvas width
        self.messages_frame.bind('<Configure>', lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>', self._on_canvas_configure)

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
        # Create a horizontal frame for this message
        msg_frame = tk.Frame(self.messages_frame)
        msg_frame.pack(fill='x', pady=2, padx=2)

        # Sender box (fixed width) - use Text to allow selection/copy
        sender_txt = tk.Text(msg_frame, width=12, height=1, wrap='none', borderwidth=1,
                             relief='groove', font=font.Font(weight='bold'))
        sender_txt.insert('1.0', sender)
        sender_txt.configure(state='disabled', padx=4, pady=2)
        sender_txt.pack(side='left', padx=(0, 6))

        # Message box (wrap text) - use Text to allow selection/copy
        # Estimate height from newline count (will still wrap visually)
        line_count = max(1, text.count('\n') + 1)
        msg_txt = tk.Text(msg_frame, wrap='word', height=min(12, line_count), borderwidth=1,
                          relief='ridge', font=font.Font(size=10))
        msg_txt.insert('1.0', text)

        # Make text widget effectively read-only but selectable/copiable:
        # leave state normal but prevent modifications via key events (allow Ctrl-C)
        def _on_key(event):
            # Allow Ctrl-C / Ctrl-Insert for copy
            if (event.state & 0x4) and event.keysym.lower() in ('c', 'insert'):
                return None
            return 'break'

        msg_txt.bind('<Key>', _on_key)
        msg_txt.bind('<Control-v>', lambda e: 'break')
        msg_txt.bind('<Button-3>', lambda e: 'break')

        # Make widget visually consistent and pack
        msg_txt.configure(padx=4, pady=4)
        msg_txt.pack(side='left', fill='x', expand=True)

        # Scroll to bottom
        self.root.update_idletasks()
        self.canvas.yview_moveto(1.0)

    def _on_canvas_configure(self, event) -> None:
        """Adjust the inner frame width to match the canvas width."""
        try:
            canvas_width = event.width
            # Update the window item width so the inner frame wraps correctly
            self.canvas.itemconfig(self.canvas_window, width=canvas_width)
        except Exception:
            # Non-fatal; ignore layout update errors
            pass

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
