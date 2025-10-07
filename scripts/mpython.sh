#!/usr/bin/bash

OPT_DIR="/opt/OpenVSP/python"
TMPDIR="/tmp/vstmp"

mkdir -p ${TMPDIR}

cp -r ${OPT_DIR}/python ${TMPDIR}/

micromamba activate vsppytools

cd ${TMPDIR}

pip install .

micromamba deactivate

rm -rf ${TMPDIR}
