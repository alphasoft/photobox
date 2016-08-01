#!/bin/sh
# use: ./do_print.sh "../output/filename"
# should return 0 if success, 1 otherwise

DEBUG="FALSE"

PRINTJOB="$1"
BOXPATH="/home/boxadmin/photobox/src/"
LPOPTIONS=" -o landscape -o position=center -o media=A5 -o ppi=287 "
if [ "$DEBUG" == "TRUE" ]; then
echo "$0: sending file ${BOXPATH}${PRINTJOB} to queue with options \"${LPOPTIONS}\" "
fi

lp $LPOPTIONS  "${BOXPATH}${PRINTJOB}" && exit 0
exit 1
