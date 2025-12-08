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

# Command line arguments
parser = argparse.ArgumentParser(description='VOICEVOX API')
parser.add_argument('-t', '--text', type=str, required=True,)
parser.add_argument('-id', '--speaker_id', type=int, default=2)
parser.add_argument('-f', '--filename', type=str,
                    default='voicevox')
parser.add_argument('-o', '--output_path', type=str, default='.')

# Parse command line arguments
args = parser.parse_args()
input_texts = args.text
speaker = args.speaker_id
filename = args.filename
output_path = args.output_path
# Create output directory if it doesn't exist
os.makedirs(output_path, exist_ok=True)

# Split text by "。" and synthesize each sentence
texts = input_texts.split('。')

# Loop for speech synthesis processing
for i, text in enumerate(texts):
    # Skip if the string is empty
    if text == '':
        continue

    # audio_query (API to create a query for speech synthesis)
    res1 = requests.post(AUDIO_QUERY_ENDPOINT,
                         params={'text': text, 'speaker': speaker})
    # synthesis (API to synthesize speech from audio query)
    res2 = requests.post(SYNTHESIS_ENDPOINT,
                         params={'speaker': speaker},
                         data=json.dumps(res1.json()))
    # Play the obtained WAV binary (if simpleaudio is available, play in memory; otherwise, save to file)
    audio_bytes = res2.content
    out_path = os.path.join(output_path, filename + f'_%03d.wav' % i)

    try:
        bio = io.BytesIO(audio_bytes)
        with wave.open(bio, 'rb') as wav_read:
            wave_obj = sa.WaveObject.from_wave_read(wav_read)
            play_obj = wave_obj.play()
            play_obj.wait_done()
    except Exception as e:
        print(f"Failed to play audio: {e}\nSaving to file instead: {out_path}")
        with open(out_path, mode='wb') as f:
            f.write(audio_bytes)
