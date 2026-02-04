#!/bin/bash
set -e

python3 -m venv /opt/venv_python_CodeneAria

/opt/venv_python_CodeneAria/bin/pip install --upgrade pip
/opt/venv_python_CodeneAria/bin/pip install --upgrade setuptools
/opt/venv_python_CodeneAria/bin/pip install \
    requests \
    Flask \
    simpleaudio \
    pytest \
    pyyaml \
    pytk \
    faster-whisper \
    torch \
    torchaudio \
    pyaudio \
    numpy
