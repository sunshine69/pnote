#!/bin/bash

usage="Usage: $0 -v version -m mailing_list_sep_by_coma -c  extra_content"

PRIME_VER='0.4.*'
# If followed by : then the option does not need a value
while getopts ":v:m:sc:h" options; do
  case $options in
    v ) VER=$OPTARG;;
    m ) MAIL_LIST=$OPTARG;;
    s ) SIMULATE='yes';;
    c ) EXTRA_CONTENT=$OPTARG;;
    h ) echo $usage 
        exit 1;;
    * ) echo $usage
        exit 1
  esac
done

if [ ! "$VER" ]; then
    current_ver=`git tag -l $PRIME_VER | tail -n 1`
    VER=`echo $current_ver | perl -ne 'print substr($_,0,4) .  (substr($_,-2) + 1)'`
    git tag $VER
#	VER=HEAD
fi

PKGNAME=pnote
BRANCH=$VER

echo "Version: '$VER'. Package name: '$PKGNAME'"

if [ ! "$MAIL_LIST" ]; then
	MAIL_LIST='msh.computing@gmail.com,kieuminhuy@gmail.com,nghiemhong_son@yahoo.com,kieuminhvn@gmail.com,kieulua@yahoo.com'
fi

# MAIL_LIST='msh.computing@gmail.com,kieusnz@yahoo.co.nz'

MAIL_SUB="pnote-${VER} release"

MAIL_MSG="To upgrade just unzip the file and copy all files inside the
pnote-VERSION/ over to your pnote directory. Read the file Changelog inside the
archives for details instructions and list of recent changes.
Have fun\n$EXTRA_CONTENT"

git whatchanged $VER | perl -ne 'BEGIN {$c=0};  /^commit [^\s]+/ and $p=1 and $c++ ; /^\:[\d]+/ and $p=undef; if ($p and $c < 4 ) { print $_ }  ' > Changelog

git archive --format tar --prefix ${PKGNAME}-${VER}/ $BRANCH | tar xf -
mv Changelog ${PKGNAME}-${VER}/
tar czf ${PKGNAME}-${VER}.tar.gz ${PKGNAME}-${VER}
if [ ! "$SIMULATE" ]; then
echo "MAIL LIST: $MAIL_LIST"
sendmail.py -m "$MAIL_MSG" -a "${PKGNAME}-${VER}.tar.gz" -s "$MAIL_SUB" -t "$MAIL_LIST" -f "msh.computing@gmail.com"
rm -rf ${PKGNAME}-${VER}
rm -f ${PKGNAME}-${VER}.tar.gz
else
echo "Simulate it, not removing the tar ball and directory.."
git tag -d $VER
fi

