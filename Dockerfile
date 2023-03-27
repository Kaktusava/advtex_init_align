FROM nvidia/cuda:11.1.1-cudnn8-devel-ubuntu18.04

RUN rm /etc/apt/sources.list.d/cuda.list && \
    apt-key del 7fa2af80 && \
    apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/machine-learning/repos/ubuntu1804/x86_64/7fa2af80.pub

RUN apt-get update &&  DEBIAN_FRONTEND="noninteractive" apt-get install -y \
    cmake \
    git \
    vim \
    wget \
    pkg-config \
    build-essential \
    libboost-all-dev \
    libopencv-dev \
    libmetis-dev \
    libpng-dev \
    libsuitesparse-dev \
    libmpfr-dev \
    libatlas-base-dev \
    liblapack-dev \
    libblas-dev \
    unzip \
    nano \
  && rm -rf /var/lib/apt/lists/*

# Download and install miniconda
RUN wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /opt/miniconda.sh \
 && chmod +x /opt/miniconda.sh \
 && /opt/miniconda.sh -b -p /opt/miniconda \
 && rm /opt/miniconda.sh \
 && echo "export PATH=/opt/miniconda/bin:$PATH" >>/root/.profile
ENV PATH=/opt/miniconda/bin:$PATH
ENV CONDA_AUTO_UPDATE_CONDA=false

# Create a Python 3.8 environment.
COPY environment.yaml /opt/environment.yaml
RUN /opt/miniconda/bin/conda install conda-build \
 && /opt/miniconda/bin/conda env create -f /opt/environment.yaml -p /opt/miniconda/envs/adv_text \
 && /opt/miniconda/bin/conda clean -ya
ENV CONDA_DEFAULT_ENV=adv_text
ENV CONDA_PREFIX=/opt/miniconda/envs/$CONDA_DEFAULT_ENV
ENV PATH=$CONDA_PREFIX/bin:$PATH