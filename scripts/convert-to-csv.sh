#!/usr/bin/env bash
#
# This script converts *.csv files from e.g. Ampliseq pipeline to *.tsv
# for use in db import via import_excel.py.
# The script takes a directory of tsv files as its only argument.
#
# convert-to-csv.sh <directory path>
#

for file in "$@"/*.tsv; do
	fullname=$(basename $file)
	path=$(dirname $file)
	name="${fullname%.*}"
	ext="${file##*.}"
	echo 'Converting' $fullname to $name'.csv'
	sed 's/'$'\t''/,/g' $file > $path/$name'.csv'
	rm $file
done
