#!/bin/sh
# use: ./check_queue.sh
# returns: 0 for an empty queue with no jobs
#          1 for one or more real printjobs containing PRINTNAME 
#          2 for only "wakeup" in queue

DEBUG="FALSE"
PRINTNAME="postcard"

set `lpq`
if [ "$DEBUG" == "TRUE" ]; then
echo "$0: \"$@\" "
fi
echo $@ | grep "no entries" && exit 0
echo $@ | grep "$PRINTNAME" && exit 1
echo $@ | grep "wakeup" && exit 2


