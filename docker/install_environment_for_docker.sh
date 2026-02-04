#!/bin/bash
set -e

ln -sf /usr/share/zoneinfo/Asia/Tokyo /etc/localtime

apt update -q
apt upgrade -y -q

apt install -y -q \
    curl \
    wget \
    gnupg \
    apt-transport-https \
    software-properties-common \
    libx11-xcb1 \
    libxkbfile1 \
    libsecret-1-0 \
    libgtk-3-0 \
    libnss3 \
    libxss1 \
    xdg-utils \
    unzip \
    aria2 \
    git \
    build-essential \
    cmake \
    gdb \
    x11-apps \
    xvfb \
    clang-format \
    nano \
    pybind11-dev \
    libasound2-dev \
    portaudio19-dev \
    libsdl2-dev \
    libportaudio2 \
    libpulse0 \
    alsa-utils \
    pulseaudio \
    fonts-noto-cjk \
    python3.12 \
    python3.12-dev \
    python3.12-venv \
    python3-tk

# install python packages in a virtual environment
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

# install llama-cpp-python with CUDA support
LD_LIBRARY_PATH=/usr/local/cuda/lib64/stubs:$LD_LIBRARY_PATH \
CMAKE_ARGS="-DGGML_CUDA=on" \
/opt/venv_python_CodeneAria/bin/pip install llama-cpp-python

rm -rf /var/lib/apt/lists/*
