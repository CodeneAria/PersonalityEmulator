from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import webbrowser
import subprocess
import os
import platform

from source.messenger.message_manager import MessageManager

from config.communcation_settings import (
    MESSENGER_PORT,
    HOSTNAME,
)

# Use context manager
# with MessageManager() as manager:
#     manager.send_message("System", "Hello!")
#     messages = manager.get_messages()
#     print(messages)

# or manual start/stop
manager = MessageManager()
manager.start()
manager.send_message("Alice", "こんにちは！")
manager.send_message("Bob", "Tkは、グラフィカルなウィンドウやウィジェットを作成するためのツールキットで、Tcl（Tool Command Language）はこれを制御するためのスプリクト言語です。これらを合わせてTcl/Tkとよびます。\n\nTkinterは、Tcl/Tk GUI ツールキットに対する標準の Python インターフェースです。このため、元であるTcl/Tkがインストールされていない場合にはTkinterも使用することができません。\n\nそこで、Tcl/Tkをインストールします。")

# open browser
url = f"http://{HOSTNAME}:{MESSENGER_PORT}"


def _is_wsl() -> bool:
    """Return True when running under WSL (Windows Subsystem for Linux)."""
    # Detect common WSL indicators: environment vars or 'microsoft' in uname release
    if os.environ.get("WSL_DISTRO_NAME"):
        return True
    if os.environ.get("WSL_INTEROP"):
        return True

    return False


if _is_wsl():
    subprocess.run(["cmd.exe", "/c", "start", url])
else:
    webbrowser.open(url)

while True:
    pass

manager.stop()
