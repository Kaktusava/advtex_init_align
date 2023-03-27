#!/bin/bash
CODE_ROOT=$PWD 

export TEX_INIT_DIR=${CODE_ROOT}/advtex_init_align/tex_init 

export THIRDPARTY_DIR=${CODE_ROOT}/third_parties 

mkdir -p ${THIRDPARTY_DIR} 

export SCENE_ID=scene_04 

conda install -c conda-forge -c fvcore fvcore 

conda install -c bottler nvidiacub 

cd ${THIRDPARTY_DIR} 

git clone https://github.com/facebookresearch/pytorch3d.git 

cd pytorch3d && git checkout 3c15a6c

pip install -e . --verbose
apt-get update &&  DEBIAN_FRONTEND="noninteractive" apt-get install mesa-common-dev 
cd ${THIRDPARTY_DIR}
wget https://gitlab.com/libeigen/eigen/-/archive/3.4/eigen-3.4.zip
unzip eigen-3.4.zip
wget https://boostorg.jfrog.io/artifactory/main/release/1.75.0/source/boost_1_75_0.tar.bz2
tar --bzip2 -xf boost_1_75_0.tar.bz2

mkdir -p ${THIRDPARTY_DIR}/boost_1_75_0/build
cd ${THIRDPARTY_DIR}/boost_1_75_0/
./bootstrap.sh --prefix=${THIRDPARTY_DIR}/boost_1_75_0/build
./b2 install

cd ${THIRDPARTY_DIR}
wget https://github.com/CGAL/cgal/releases/download/v5.1.5/CGAL-5.1.5.zip
unzip CGAL-5.1.5.zip
cd ${THIRDPARTY_DIR}/CGAL-5.1.5 && mkdir install && mkdir build && cd build
cmake -DCGAL_HEADER_ONLY=OFF -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=../install ..
make
make install

cd ${TEX_INIT_DIR}
make tex_init DEBUG=0 -j 8