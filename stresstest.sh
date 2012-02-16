#!/bin/bash

# This script is the entry point for the Python stress test program.

INPUT_LOG_FILE="input.txt"
OUTPUT_LOG_FILE="responseTimer.log"
RESULTS_DIR=$(date "+%Y%m%d_%H%M%S")

STRESSTEST_SCRIPT=stresstest.py
# NOTE: This functionality is currently not ready, but I'm leaving it here
# for simple inclusion once it is.
#LOG_ANALYSIS_SCRIPT=../loganalysis/src/analyzer.py

# Make sure we have a requestTimer file to start with
if [ ! -f ${INPUT_LOG_FILE} ]; then
    echo "${INPUT_LOG_FILE} does not exist!"
    exit 0
fi

# Make a directory with the current time as the name
mkdir ${RESULTS_DIR}

# Run Python script
# (returns a .out file for each process, and stresstest.log with test info)
python ${STRESSTEST_SCRIPT} 2>stresstest.err

# Throw all of the .out files together and sort them
cat *.out | sort > ${OUTPUT_LOG_FILE}

# Compress the .out files and throw the originals away
tar czvf rawoutput.tar.gz *.out
rm *.out

# Run log analysis scripts
#python ${LOG_ANALYSIS_SCRIPT} ${OUTPUT_LOG_FILE}

# Build graphs (with gnuplot?)
# TODO...

# Move everything to the results directory
mv ${OUTPUT_LOG_FILE} rawoutput.tar.gz stresstest.log stresstest.err *.txt ${RESULTS_DIR}

