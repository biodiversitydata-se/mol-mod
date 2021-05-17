#!/bin/bash -e

# Pull web dependencies

JQJS=https://code.jquery.com/jquery-3.6.0.min.js
DTCSS=https://cdn.datatables.net/1.10.24/css/jquery.dataTables.min.css
DTJS=https://cdn.datatables.net/1.10.24/js/jquery.dataTables.min.js
BS=https://github.com/twbs/bootstrap/releases/download/v3.4.1/bootstrap-3.4.1-dist.zip
SELECTTWO=https://github.com/select2/select2/archive/refs/tags/4.0.13.tar.gz
FONTAWESOME=https://use.fontawesome.com/releases/v5.15.3/fontawesome-free-5.15.3-web.zip



STATICDIR=$(dirname "$(realpath "$0")")/../molmod/static
TDIR=${TMPDIR:-/tmp}/collectscripts$$

mkdir -p "$TDIR"
pushd "$TDIR"

mkdir -p js
mkdir -p css
mkdir -p webfonts

mkdir -p "$STATICDIR/webfonts"
mkdir -p "$STATICDIR/css"
mkdir -p "$STATICDIR/js"


wget "$DTJS"
wget "$DTCSS"
wget "$JQJS"

mv jquery-*.min.js js/jquery.min.js
mv *.js js
mv *.css css

wget "$BS"
wget "$SELECTTWO"
wget "$FONTAWESOME"

unzip bootstrap*.zip
unzip fontawesome*.zip
tar -zxvf *.tar.gz

cp bootstrap*/js/bootstrap.min.js js/
cp select2*/dist/js/select2.full.min.js js/
cp fontawesome*/js/all.min.js js/fontawesome.all.min.js
cp fontawesome*/js/brands.js js/brands.min.js

cp bootstrap*/css/bootstrap.min.css css/
cp bootstrap*/css/bootstrap.min.css.map css/
cp select2*/dist/css/select2.min.css css/
cp fontawesome*/css/all.min.css css/fontawesome.all.min.cs
cp fontawesome*/css/brands.min.css css/brands.min.cs

cp fontawesome*/webfonts/* webfonts/


curl -s 'https://google-webfonts-helper.herokuapp.com/api/fonts/roboto?subsets=latin,latin-ext' | \
	jq -r '.variants[] | [ .id, .fontStyle, .fontWeight, .ttf, .woff, .woff2] | @tsv'  | \
	while read -r fontid style weight ttffile wofffile woff2file ; do
		curl -s "$ttffile" > "webfonts/roboto-$weight-style.ttf"
			echo $fontid
		curl -s "$ttffile" > "webfonts/roboto-$weight-$style.ttf"
		curl -s "$wofffile" > "webfonts/roboto-$weight-$style.woff"
		curl -s "$woff2file" > "webfonts/roboto-$weight-$style.woff2"

		cat - >> css/roboto.css <<EOF
@font-face {
	font-family: Roboto;
	font-style: $style;
	font-weight: $weight;
	font-display: swap;
	src: url(/static/webfonts/roboto-$weight-$style.ttf) format('truetype'),
	     url(/static/webfonts/roboto-$weight-$style.woff) format('woff'),
	     url(/static/webfonts/roboto-$weight-$style.woff2) format('woff2');
}
EOF

done

cat css/* > css/unified.css

cp webfonts/* "$STATICDIR/webfonts/"
cp css/* "$STATICDIR/css/"
cp js/* "$STATICDIR/js/"

popd
rm -r "$TDIR"