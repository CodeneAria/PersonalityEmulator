FROM nvidia/cuda:12.8.0-devel-ubuntu24.04

COPY install_ubuntu_apps.sh /

RUN chmod +x /install_ubuntu_apps.sh && \
    /install_ubuntu_apps.sh

COPY install_python_packages.sh /

RUN chmod +x /install_python_packages.sh && \
    /install_python_packages.sh

COPY install_llama_cpp_python.sh /

RUN chmod +x /install_llama_cpp_python.sh && \
    /install_llama_cpp_python.sh
