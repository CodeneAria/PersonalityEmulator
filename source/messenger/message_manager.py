"""Message manager module for controlling ChatWindow subprocess."""
from __future__ import annotations

import os
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
sys.path.append(str(Path(__file__).resolve().parents[2]))

import subprocess
import time
import threading
from typing import Optional, Union
import requests

from config.communcation_settings import (
    MESSENGER_PORT,
    HOSTNAME,
    RESPONSE_STATUS_CODE_SUCCESS,
    RESPONSE_STATUS_CODE_NOT_FOUND,
    RESPONSE_STATUS_CODE_ERROR,
)


class MessageManager:
    """Manager class for controlling ChatWindow in a separate process.

    This class starts the chat_window_gui.py as a subprocess and communicates
    with it via HTTP requests. The subprocess runs both the Flask server
    and the Tkinter GUI.
    """

    def __init__(
        self,
        host: str = HOSTNAME,
        port: int = MESSENGER_PORT
    ):
        """Initialize MessageManager.

        Args:
            host: Hostname for the ChatWindow server.
            port: Port number for the ChatWindow server.
        """
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.process: Optional[subprocess.Popen] = None

    def start(self, wait_time: float = 2.0) -> bool:
        """Start ChatWindow subprocess.

        Args:
            wait_time: Time to wait for server to start (seconds).

        Returns:
            True if server started successfully, False otherwise.
        """
        if self.process is not None:
            return True

        chat_window_script = Path(
            __file__).resolve().parent / "chat_window_gui.py"

        try:
            self.process = subprocess.Popen(
                [sys.executable, str(chat_window_script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Wait for server to start
            time.sleep(wait_time)

            # Check if process is still running
            if self.process.poll() is not None:
                print("ChatWindow process terminated unexpectedly")
                self.process = None
                return False

            # Verify server is responding
            try:
                response = requests.get(f"{self.base_url}/health", timeout=5)
                if response.status_code != RESPONSE_STATUS_CODE_SUCCESS:
                    print(
                        f"ChatWindow health check failed: {response.status_code}")
                    return False
            except requests.exceptions.RequestException:
                print("ChatWindow server is not responding")
                return False

            return True
        except Exception as e:
            print(f"Failed to start ChatWindow: {e}")
            return False

    def stop(self) -> None:
        """Stop ChatWindow subprocess."""
        if self.process is not None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            self.process = None

    def is_running(self) -> bool:
        """Check if ChatWindow process is running.

        Returns:
            True if running, False otherwise.
        """
        if self.process is None:
            return False

        # Check if process is still alive
        return self.process.poll() is None

    def send_message(self, sender: str, text: str) -> bool:
        """Send a message to the ChatWindow.

        Args:
            sender: Message sender name.
            text: Message text.

        Returns:
            True if message was sent successfully, False otherwise.
        """
        try:
            response = requests.post(
                f"{self.base_url}/messages",
                json={"sender": sender, "text": text},
                timeout=5
            )
            return response.status_code == 201
        except requests.exceptions.RequestException as e:
            print(f"Failed to send message: {e}")
            return False

    def get_messages(self) -> list[dict]:
        """Get all messages from the ChatWindow.

        Returns:
            List of message dictionaries, or empty list on error.
        """
        try:
            response = requests.get(
                f"{self.base_url}/messages",
                timeout=5
            )
            if response.status_code == RESPONSE_STATUS_CODE_SUCCESS:
                return response.json()
            return []
        except requests.exceptions.RequestException as e:
            print(f"Failed to get messages: {e}")
            return []

    def clear_messages(self) -> bool:
        """Clear all messages in the ChatWindow.

        Returns:
            True if messages were cleared successfully, False otherwise.
        """
        try:
            response = requests.post(
                f"{self.base_url}/messages/clear",
                timeout=5
            )
            return response.status_code == RESPONSE_STATUS_CODE_SUCCESS
        except requests.exceptions.RequestException as e:
            print(f"Failed to clear messages: {e}")
            return False

    def health_check(self) -> bool:
        """Check if the ChatWindow server is healthy.

        Returns:
            True if server is healthy, False otherwise.
        """
        try:
            response = requests.get(
                f"{self.base_url}/health",
                timeout=5
            )
            return response.status_code == RESPONSE_STATUS_CODE_SUCCESS
        except requests.exceptions.RequestException:
            return False

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()


if __name__ == "__main__":
    # Simple test
    import time

    print("Starting MessageManager...")
    manager = MessageManager()

    if manager.start():
        print("ChatWindow started successfully!")

        # Send some test messages
        manager.send_message("System", "Hello from MessageManager!")
        time.sleep(1)
        manager.send_message("User", "This is a test message.")
        time.sleep(1)

        # Get messages
        messages = manager.get_messages()
        print(f"Messages: {messages}")

        # Keep running for a bit
        print("Press Ctrl+C to stop...")
        try:
            while manager.is_running():
                time.sleep(1)
        except KeyboardInterrupt:
            pass

        manager.stop()
        print("ChatWindow stopped.")
    else:
        print("Failed to start ChatWindow.")
