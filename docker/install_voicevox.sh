#!/bin/bash
set -e

mkdir -p /opt/voicevox_engine
cd /opt/voicevox_engine

aria2c -x 16 -s 16 https://github.com/VOICEVOX/voicevox_engine/releases/download/0.25.1/voicevox_engine-linux-nvidia-0.25.1.7z.001
aria2c -x 16 -s 16 https://github.com/VOICEVOX/voicevox_engine/releases/download/0.25.1/voicevox_engine-linux-nvidia-0.25.1.7z.002

7z x voicevox_engine-linux-nvidia-0.25.1.7z.001
rm voicevox_engine-linux-nvidia-0.25.1.7z.00*

chmod +x voicevox_engine-linux-nvidia-0.25.1/run
