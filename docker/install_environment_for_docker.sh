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
apt install -y -q fonts-noto-cjk

# install python3.12
apt install -y -q python3.12 python3.12-dev python3.12-venv
python3 -m venv /opt/venv_python_CodeneAria

/opt/venv_python_CodeneAria/bin/pip install --upgrade pip
/opt/venv_python_CodeneAria/bin/pip install --upgrade setuptools
/opt/venv_python_CodeneAria/bin/pip install requests Flask simpleaudio pytest pyyaml pytk
apt install -y -q python3-tk

## Clone repositories
cd /opt
mkdir CodeneAria
cd ./CodeneAria

git clone --recursive https://github.com/CodeneAria/PersonalityEmulator.git

rm -rf /var/lib/apt/lists/*
