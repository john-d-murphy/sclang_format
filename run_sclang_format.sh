#!/bin/bash

# Current Directory
# see: https://stackoverflow.com/questions/4774054/reliable-way-for-a-bash-script-to-get-the-full-path-to-itself
SCRIPT_HOME=`dirname $0 | while read a; do cd $a && pwd && break; done`

cd ${SCRIPT_HOME}

# Run Script with Local Defaults - if this doesn't work, make sure you've run 'pipenv update' beforehand
pipenv run python ${SCRIPT_HOME}/src/sclang_format.py -f $1 -l $2
