#!/bin/sh
# use ./do_compose.sh "Motivfile" "Motiv.data" "Face" "snapshot.data" "Compositionfile"

 EBUG="FALSE"
COMPOSEOPTIONS=" -1g -f20 -v "

if [ "$DEBUG" == "TRUE" ]; then
echo "$0: options:\"${COMPOSEOPTIONS}\",generating \"$5\" from Motiv:\"$1\" Motiv.data:\"$2\" Face:\"$3\" snaphot.data:\"$4\" " 
fi

/home/boxadmin/photobox/src/compose ${COMPOSEOPTIONS} $1 $2 $3 $4 $5 &&exit 0
exit 1

