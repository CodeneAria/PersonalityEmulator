#!/bin/bash
set -e

LD_LIBRARY_PATH=/usr/local/cuda/lib64/stubs:$LD_LIBRARY_PATH \
CMAKE_ARGS="-DGGML_CUDA=on" \
/opt/venv_python_CodeneAria/bin/pip install llama-cpp-python

rm -rf /var/lib/apt/lists/*
