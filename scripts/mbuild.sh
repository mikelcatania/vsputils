#!/usr/bin/bash

MAIN_DIR="/home/mikel/aguro/cfd/OpenVSP"

# Check if an argument is provided, and override MAIN_DIR if so
if [ "$1" ]; then
    MAIN_DIR="$1"
fi

cd $MAIN_DIR

# Update repo
cd repo
git pull

# Build external libs
mkdir -p ${MAIN_DIR}/buildlibs
cd ${MAIN_DIR}/buildlibs
rm -rf *

cmake -DVSP_USE_SYSTEM_ADEPT2=false -DVSP_USE_SYSTEM_CLIPPER2=false -DVSP_USE_SYSTEM_CMINPACK=false -DVSP_USE_SYSTEM_CODEELI=false -DVSP_USE_SYSTEM_CPPTEST=false -DVSP_USE_SYSTEM_DELABELLA=false -DVSP_USE_SYSTEM_EIGEN=false -DVSP_USE_SYSTEM_EXPRPARSE=false -DVSP_USE_SYSTEM_FLTK=false -DVSP_USE_SYSTEM_GLEW=true -DVSP_USE_SYSTEM_GLM=false -DVSP_USE_SYSTEM_LIBIGES=false -DVSP_USE_SYSTEM_LIBXML2=true -DVSP_USE_SYSTEM_OPENABF=false -DVSP_USE_SYSTEM_PINOCCHIO=false -DVSP_USE_SYSTEM_STEPCODE=false -DVSP_USE_SYSTEM_TRIANGLE=false ../repo/Libraries -DCMAKE_BUILD_TYPE=Release

make -j8

# Build libs
mkdir -p ${MAIN_DIR}/build
cd ${MAIN_DIR}/build
rm -rf *

cmake ../repo/src/ -DVSP_LIBRARY_PATH=${MAIN_DIR}/buildlibs -DCMAKE_BUILD_TYPE=Release -DVSP_CPACK_GEN=DEB

make -j8

# Install package
make package

DEB_FILE=$(ls *.deb 2>/dev/null)

if [ -z "$DEB_FILE" ]; then
    echo "No .deb file found in the directory."
    exit 1
else
    echo "Found .deb file: $DEB_FILE"
fi

#sudo dpkg -i ${DEB_FILE} 
