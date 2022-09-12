#!/bin/bash -e

# Pull web dependencies

DTCSS=https://cdn.datatables.net/v/bs/jszip-2.5.0/dt-1.12.1/b-2.2.3/b-html5-2.2.3/sl-1.4.0/datatables.min.css
DTJS=https://cdn.datatables.net/v/bs/jszip-2.5.0/dt-1.12.1/b-2.2.3/b-html5-2.2.3/sl-1.4.0/datatables.min.js

SELECTTWO=https://github.com/select2/select2/archive/refs/tags/4.0.13.tar.gz
SELECTTWOBS=https://raw.githubusercontent.com/select2/select2-bootstrap-theme/master/dist/select2-bootstrap.min.css

STATICDIR=$(dirname "$(realpath "$0")")/../molmod/static
TDIR=${TMPDIR:-/tmp}/collectscripts$$

mkdir -p "$TDIR"
pushd "$TDIR"

mkdir -p js
mkdir -p css
mkdir -p webfonts
mkdir -p img

mkdir -p "$STATICDIR/webfonts"
mkdir -p "$STATICDIR/css"
mkdir -p "$STATICDIR/js"
mkdir -p "$STATICDIR/img"

wget "$DTJS"
wget "$DTCSS"
wget "$SELECTTWOBS"
mv ./*.js js
mv ./*.css css

wget "$SELECTTWO"

tar -zxvf ./*.tar.gz

cp select2*/dist/js/select2.full.min.js js/
cp select2*/dist/css/select2.min.css css/

if [ skip = this_for_now ]; then

	curl -s 'https://google-webfonts-helper.herokuapp.com/api/fonts/roboto?subsets=latin,latin-ext' | \
		jq -r '.variants[] | [ .id, .fontStyle, .fontWeight, .ttf, .woff, .woff2] | @tsv'  | \
		while read -r fontid style weight ttffile wofffile woff2file ; do
			curl -s "$ttffile" > "webfonts/roboto-$weight-style.ttf"
			curl -s "$ttffile" > "webfonts/roboto-$weight-$style.ttf"
			curl -s "$wofffile" > "webfonts/roboto-$weight-$style.woff"
			curl -s "$woff2file" > "webfonts/roboto-$weight-$style.woff2"

		cat - >> css/roboto.css <<EOF
@font-face {
	font-family: Roboto;
	font-style: $style;
	font-weight: $weight;
	font-display: swap;
	src: url(/static/webfonts/roboto-$weight-$style.woff2) format('woff2'),
         url(/static/webfonts/roboto-$weight-$style.woff) format('woff'),
		 url(/static/webfonts/roboto-$weight-$style.ttf) format('truetype');
}
EOF
	done
fi

cp css/* "$STATICDIR/css/"
cp js/* "$STATICDIR/js/"

popd
rm -r "$TDIR"
