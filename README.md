# Personality Emulator

ローカル LLM を用いて特定のキャラクター（人格）をエミュレートする会話システムです。  
テキスト入力・音声入力の両方に対応し、生成した応答をテキストと音声で返します。

## 概要

- **LLM 推論**: [llama-cpp-python](https://github.com/abetlen/llama-cpp-python) を使用し、GGUF 形式のモデルをローカルで実行します。
- **音声入力**: [Whisper](https://github.com/openai/whisper) ベースの音声認識でマイク入力をテキストに変換します。
- **音声出力**: [VOICEVOX](https://voicevox.hiroshiba.jp/) を使用して応答テキストを音声合成します。
- **チャット UI**: ブラウザで開ける HTML ベースのチャットウィンドウを提供します。

現在のデフォルト人格設定は 博麗霊夢（東方 Project）です。

## システム要件

- Ubuntu 24.04
- RAM 32GB以上推奨
- CUDA 12.8 が動作するGPU
- VRAM 12GB以上推奨

WSL Ubuntu 24.04でも動作しますが、Dockerの設定はそのままでは使えません。

WSLの場合は個別にツールをインストールすることをお勧めします。

## 環境

Dev Container（Docker）による開発環境が用意されています。  
VS Code の Remote Containers 拡張機能を利用して `docker/docker-compose.yml` をベースにコンテナを起動できます。

## 使い方

### 1. モデルの準備

`llm/` ディレクトリに GGUF 形式のモデルを配置します。  
`configuration/person_settings.py` の `LLM_MODEL_PATH` を適宜変更してください。  
モデルが存在しない場合は `LLM_MODEL_DOWNLOAD_PATH` に指定した URL から自動ダウンロードされます。

### 2. VOICEVOX のインストール

VOICEVOXは、Dockerイメージ作成のタイミングでWebからダウンロードされます。

### 3. 実行

```bash
python run.py
```

起動後、ターミナルに表示される URL（例: `http://localhost:50050`）をブラウザで開くとチャットウィンドウが表示されます。

## システム構成

概要クラス図

![概要クラス図](./document/system/architecture-概要クラス図.svg)

| Path | 説明 |
| --- | --- |
| `run.py` | エントリポイント |
| `source/` | ソースコード |
| `source/personality_model_runner.py` | 各コンポーネントを統合するメインランナー |
| `source/core/` | コア（LLM 管理・プロンプト生成） |
| `source/core/personality_core_manager.py` | LLM のライフサイクル管理・ストリーミング生成 |
| `source/core/prompt_generator.py` | システムプロンプト生成 |
| `source/messenger/` | チャット関連（UI/メッセージ管理） |
| `source/messenger/message_manager.py` | チャットウィンドウ管理（サブプロセス制御） |
| `source/messenger/chat_window_gui.py` | Flask + Tkinter によるチャット UI |
| `source/voice/` | 音声入出力関連 |
| `source/voice/voice_manager.py` | 音声入出力の統合管理 |
| `source/voice/listener/speech_recognizer.py` | 音声認識（Whisper） |
| `source/voice/speaker/voice_generator.py` | 音声生成キュー管理 |
| `source/voice/speaker/voicevox_communicator.py` | VOICEVOX API クライアント |
| `configuration/` | モデル・キャラクター・通信設定 |
| `personality/` | キャラクター設定ファイル（人物情報・世界観など） |
| `llm/` | GGUF モデルファイル置き場 |
| `docker/` | Dev Container 用 Docker 設定 |

## ライセンス

MIT License - 詳細は [LICENSE](./LICENSE.txt) を参照してください。
