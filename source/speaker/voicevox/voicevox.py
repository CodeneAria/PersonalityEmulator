import requests
import argparse
import json
import os
import sys
from pathlib import Path
from source.speaker.audio_speaker import AudioSpeaker

sys.path.append(str(Path(__file__).resolve().parents[1]))
sys.path.append(str(Path(__file__).resolve().parents[2]))
sys.path.append(str(Path(__file__).resolve().parents[3]))

from config.communcation_settings import (
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
# Initialize AudioSpeaker with output directory
audio_speaker = AudioSpeaker(fallback_dir=output_path)

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
    # Play the obtained WAV binary using AudioSpeaker
    audio_bytes = res2.content
    fallback_name = f"{filename}_{i:03d}"
    audio_speaker.play(audio_bytes, fallback_filename=fallback_name)
