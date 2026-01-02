from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from source.messenger.message_manager import MessageManager

# # コンテキストマネージャを使用
# with MessageManager() as manager:
#     manager.send_message("System", "Hello!")
#     messages = manager.get_messages()
#     print(messages)

# または明示的に制御
manager = MessageManager()
manager.start()
manager.send_message("Alice", "こんにちは！")
manager.send_message("Bob", "Tkは、グラフィカルなウィンドウやウィジェットを作成するためのツールキットで、Tcl（Tool Command Language）はこれを制御するためのスプリクト言語です。これらを合わせてTcl/Tkとよびます。\n\nTkinterは、Tcl/Tk GUI ツールキットに対する標準の Python インターフェースです。このため、元であるTcl/Tkがインストールされていない場合にはTkinterも使用することができません。\n\nそこで、Tcl/Tkをインストールします。")
manager.stop()
