ln -sf /usr/share/zoneinfo/Asia/Tokyo /etc/localtime

apt update -q
apt upgrade -y -q

apt install -y -q curl \
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
    libasound2 \
    xdg-utils \
    unzip \

apt update -q

apt install -y curl
apt install -y wget
apt install -y aria2
apt install -y -q git
apt install -y -q build-essential
apt install -y -q cmake
apt install -y -q gdb
apt install -y -q x11-apps
apt install -y -q xvfb
apt install -y -q clang-format
apt install -y -q nano
apt install -y -q pybind11-dev
apt install -y -q libasound2-dev
apt install -y -q portaudio19-dev
apt install -y -q libasound2
apt install -y -q libsdl2-dev
apt install -y -q alsa-utils
apt install -y -q pulseaudio
apt install -y -q fonts-noto-cjk

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

# install python3.12
apt install -y -q python3.12 python3.12-dev python3.12-venv
python3 -m venv /opt/venv_python_CodeneAria

/opt/venv_python_CodeneAria/bin/pip install --upgrade pip
/opt/venv_python_CodeneAria/bin/pip install --upgrade setuptools
/opt/venv_python_CodeneAria/bin/pip install requests Flask simpleaudio pytest pyyaml pytk
apt install -y -q python3-tk

rm -rf /var/lib/apt/lists/*
