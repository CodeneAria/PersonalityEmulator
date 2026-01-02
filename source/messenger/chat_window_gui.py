import tkinter as tk
from tkinter import scrolledtext
from tkinter import font
import requests
from requests.exceptions import RequestException
import threading
import time

# ====== 設定 ======
API_ENDPOINT = "http://localhost:50050/messages"  # メッセージ取得用 REST API
POLL_INTERVAL = 2  # API をポーリングする間隔（秒）

# ====== GUI ======


class ChatWindow:

    def __init__(self, root):
        self.root = root
        root.title("Chat Window")

        # 日本語フォントを指定
        jp_font = font.Font(family="Meiryo", size=10)

        # 履歴表示スペース（スクロールテキスト）
        self.history = scrolledtext.ScrolledText(
            root, state='disabled', height=20, width=50, font=jp_font)
        self.history.grid(row=0, column=0, padx=10, pady=10)

        # REST API 用スレッドを開始
        self.last_id = 0
        self.fetch_thread = threading.Thread(
            target=self.fetch_loop, daemon=True)
        self.fetch_thread.start()

    def add_message(self, sender, text):
        """チャット履歴に表示する関数."""
        self.history.config(state='normal')
        self.history.insert(tk.END, f"{sender}: {text}\n")
        self.history.yview(tk.END)     # 自動スクロール
        self.history.config(state='disabled')

    def fetch_loop(self):
        """
        一定間隔で API を叩き、
        新しいメッセージがあれば表示するループ。
        """
        while True:
            try:
                resp = requests.get(API_ENDPOINT, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list):
                        for msg in data:
                            msg_id = msg.get("id", 0)
                            # id が前回より新しい場合だけ表示
                            if msg_id > self.last_id:
                                self.last_id = msg_id
                                sender = msg.get("sender", "")
                                text = msg.get("text", "")
                                self.root.after(0, self.add_message,
                                                sender, text)
            except RequestException:
                # サーバ未起動などの接続関連エラーは黙って待つ
                pass
            except Exception as e:
                print("API Fetch Error:", e)
            time.sleep(POLL_INTERVAL)


# ====== 実行 ======
if __name__ == "__main__":
    root = tk.Tk()
    app = ChatWindow(root)
    root.mainloop()
