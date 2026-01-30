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
    libasound2t64 \
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
    libasound2 \
    libsdl2-dev \
    alsa-utils \
    pulseaudio \
    fonts-noto-cjk \
    python3.12 \
    python3.12-dev \
    python3.12-venv \
    python3-tk

# Install NVIDIA CUDA toolkit if an NVIDIA GPU is present
if command -v nvidia-smi >/dev/null 2>&1 || \
     (command -v lspci >/dev/null 2>&1 && lspci | grep -i nvidia >/dev/null 2>&1) || \
     [ -e /dev/nvidiactl ] ; then
    echo "NVIDIA GPU detected — installing nvidia-cuda-toolkit"
    apt update -q
    apt install -y -q nvidia-cuda-toolkit
else
    echo "No NVIDIA GPU detected — skipping nvidia-cuda-toolkit"
fi

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

rm -rf /var/lib/apt/lists/*
