:
new=`basename $1 .bmp`
now=`date +%F-%T`
#echo converting $1 to /home/boxadmin/photobox/output/save/${new}_${now}.png
convert $1 /home/boxadmin/photobox/output/save/${new}_${now}.png 
#mv $new save/postcard_`date +%F-%T`.png
