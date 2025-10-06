# Start from the Ubuntu 24.04 base image
FROM ubuntu:24.04 AS setup

# Set environment variables to avoid interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

# Update the package list and install dependencies
RUN apt-get update && apt-get install -y \
    python3-dev \
    git \
    git-gui \
    cmake \
    libxml2-dev \
    libfltk1.3-dev \
    g++ \
    libjpeg-dev \
    libglm-dev \
    libcminpack-dev \
    libglew-dev \
    swig \
    file \
    desktop-file-utils \
    && apt-get clean

FROM setup AS build

# Make dirs and copy source
ARG OD=/tmp/OpenVSP
RUN mkdir -p ${OD}/build
RUN mkdir -p ${OD}/buildlibs
RUN mkdir -p ${OD}/repo

# Copy source. Pass arg from command line options:
# --build-arg REPO_PATH=...
ARG REPO_PATH
COPY ${REPO_PATH} ${OD}/repo

# Build ext libraries
WORKDIR ${OD}/buildlibs

RUN cmake \
  -DVSP_USE_SYSTEM_ADEPT2=false \
  -DVSP_USE_SYSTEM_CLIPPER2=false \ 
  -DVSP_USE_SYSTEM_CMINPACK=false \
  -DVSP_USE_SYSTEM_CODEELI=false \
  -DVSP_USE_SYSTEM_CPPTEST=false \
  -DVSP_USE_SYSTEM_DELABELLA=false \ 
  -DVSP_USE_SYSTEM_EIGEN=false \
  -DVSP_USE_SYSTEM_EXPRPARSE=false \ 
  -DVSP_USE_SYSTEM_FLTK=false \
  -DVSP_USE_SYSTEM_GLEW=true \
  -DVSP_USE_SYSTEM_GLM=false \
  -DVSP_USE_SYSTEM_LIBIGES=false \ 
  -DVSP_USE_SYSTEM_LIBXML2=true \
  -DVSP_USE_SYSTEM_OPENABF=false \
  -DVSP_USE_SYSTEM_PINOCCHIO=false \ 
  -DVSP_USE_SYSTEM_STEPCODE=false \
  -DVSP_USE_SYSTEM_TRIANGLE=false \
  ${OD}/repo/Libraries -DCMAKE_BUILD_TYPE=Release
RUN make -j 8

# Build OpenVSP
WORKDIR ${OD}/build
RUN cmake ../repo/src/ \
  -DVSP_LIBRARY_PATH=${OD}/buildlibs \
  -DCMAKE_BUILD_TYPE=Release \
  -DVSP_NO_GRAPHICS=true \
  -DVSP_NO_HELP=true \
  -DVSP_NO_DOC=true \
  -DVSP_NO_PYDOC=true \
  -DVSP_CPACK_GEN=DEB
RUN make -j 8
RUN make package
RUN DEB_FILE=$(find . -type f -maxdepth 1 -name "*.deb") && \
   cp $DEB_FILE /tmp/


FROM setup

COPY --from=build /tmp/*deb /tmp/ovsp.deb
RUN dpkg -i /tmp/ovsp.deb && rm /tmp/ovsp.deb

# Create running dir
VOLUME /tmp/wdir
WORKDIR /tmp/wdir
