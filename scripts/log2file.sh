#!/bin/sh
# use: ./log2file.sh "logfilename" "text you want to log"
# returns 0 if success, 1 otherwise

DEBUG="FALSE"


LOGFILE="$1"
shift
LOGTEXT="$@"
BOXPATH="/home/boxadmin/photobox/output/"
if [ "$DEBUG" == "TRUE" ]; then
echo "$0: logging \"${LOGTEXT}\" -> ${BOXPATH}${LOGFILE}"
fi


echo ${LOGTEXT} >> ${BOXPATH}${LOGFILE} && exit 0
exit 1