#!/bin/bash
set -e

ln -s /usr/local/cuda/lib64/stubs/libcuda.so /usr/local/cuda/lib64/stubs/libcuda.so.1

export CUDA_HOME=/usr/local/cuda
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64/stubs:$LD_LIBRARY_PATH

CMAKE_ARGS="-DGGML_CUDA=on -DCMAKE_LIBRARY_PATH=/usr/local/cuda/lib64/stubs" \
/opt/venv_python_CodeneAria/bin/pip install llama-cpp-python

rm /usr/local/cuda/lib64/stubs/libcuda.so.1

rm -rf /var/lib/apt/lists/*
