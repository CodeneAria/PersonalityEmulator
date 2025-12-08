import requests
import argparse
import json
import io
import wave
import os
import simpleaudio as sa

from config.communcation_settings import (
    HOSTNAME,
    VOICEVOX_PORT,
    AUDIO_QUERY_ENDPOINT,
    SYNTHESIS_ENDPOINT,
    SPEAKER_ID_KASUKABE_TSUMUGI
)

# コマンド引数
parser = argparse.ArgumentParser(description='VOICEVOX API')
parser.add_argument('-t', '--text', type=str, required=True,)
parser.add_argument('-id', '--speaker_id', type=int, default=2)
parser.add_argument('-f', '--filename', type=str,
                    default='voicevox')
parser.add_argument('-o', '--output_path', type=str, default='.')

# コマンド引数分析
args = parser.parse_args()
input_texts = args.text
speaker = args.speaker_id
filename = args.filename
output_path = args.output_path
# 出力パスを作成（存在しない場合）
os.makedirs(output_path, exist_ok=True)

# 「 。」で文章を区切り１行ずつ音声合成させる
texts = input_texts.split('。')

# 音声合成処理のループ
for i, text in enumerate(texts):
    # 文字列が空の場合は処理しない
    if text == '':
        continue

    # audio_query (音声合成用のクエリを作成するAPI)
    res1 = requests.post(AUDIO_QUERY_ENDPOINT,
                         params={'text': text, 'speaker': speaker})
    # synthesis (音声合成するAPI)
    res2 = requests.post(SYNTHESIS_ENDPOINT,
                         params={'speaker': speaker},
                         data=json.dumps(res1.json()))
    # 取得した WAV バイナリを再生（simpleaudio があればメモリ再生、なければファイルに保存）
    audio_bytes = res2.content
    out_path = os.path.join(output_path, filename + f'_%03d.wav' % i)

    try:
        bio = io.BytesIO(audio_bytes)
        with wave.open(bio, 'rb') as wav_read:
            wave_obj = sa.WaveObject.from_wave_read(wav_read)
            play_obj = wave_obj.play()
            play_obj.wait_done()
    except Exception as e:
        print(f"再生に失敗しました: {e}\n代わりにファイルへ保存します: {out_path}")
        with open(out_path, mode='wb') as f:
            f.write(audio_bytes)
