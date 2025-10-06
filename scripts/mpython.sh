#!/usr/bin/bash

MAIN_DIR="/home/mikel/aguro/cfd/OpenVSP/python"
OPT_DIR="/opt/OpenVSP/python"

# Check if an argument is provided, and override MAIN_DIR if so
if [ "$1" ]; then
    MAIN_DIR="$1"
fi

echo "Differences in environment":
diff ${MAIN_DIR}/environment.yml ${OPT_DIR}/environment.yml
echo

echo "Differences in reqs:"
diff ${MAIN_DIR}/requirements-dev.txt ${OPT_DIR}/requirements-dev.txt
echo

echo "Copying python directories"
cp -rp ${OPT_DIR}/* ${MAIN_DIR}

