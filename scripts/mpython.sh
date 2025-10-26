#!/usr/bin/bash

OPT_DIR="/opt/OpenVSP/python"
TMPDIR="/tmp/vstmp"

mkdir -p ${TMPDIR}

cp -r ${OPT_DIR}/ ${TMPDIR}/

micromamba activate vsppytools

cd ${TMPDIR}/python

pip install -r requirements.txt

micromamba deactivate

rm -rf ${TMPDIR}
