#!/usr/bin/env bash

# Mapping of the data file's column names to database field names.
declare -A field_name_map
field_name_map=(
	[kingdom]=kingdom
	[phylum]=phylum
	[class]=class
	[order]=oorder
	[family]=family
	[genus]=genus
	[specificEpithet]=specific_epithet
	[infraspecificEpithet]=infraspecific_epithet
	[otu]=otu
	[scientificName]=scientific_name
	[taxonRank]=taxon_rank
	[date_identified]=date_identified
	[reference_db]=reference_db
	[annotation_algorithm]=annotation_algorithm
	[identification_references]=identification_references
	[annotation_confidence]=annotation_confidence
	[taxon_remarks]=taxon_remarks
)

readlink () {
	case $OSTYPE in
		linux*)
			command readlink "$@" ;;
		*)
			command greadlink "$@" ;;
	esac
}

asvhash () {
	printf '%s' "$1" |
	case $OSTYPE in
		linux*)
			command md5sum |
			cut -d ' ' -f 1
			;;
		*)
			command md5 ;;
	esac |
	awk '{ print "ASV:" $0 }'
}

do_dbquery () {
        # Use --command if we got an argument.  Otherwise, read SQL
        # commands from standard input.

	if [ "$#" -ne 0 ]; then
		set -- --command="$*"
	fi

	docker exec -i asv-db \
		psql -h localhost -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
		--no-align --quiet --tuples-only "$@"
}

topdir=$( readlink -f "$( dirname "$0" )/.." )

if [ ! -e "$topdir/.env" ]; then
	printf 'Can not see "%s" to read database configuration.\n' "$topdir/.env"
	exit 1
fi >&2

if [ "$( docker container inspect -f '{{ .State.Running }}' asv-db )" != 'true' ]
then
	echo 'Container "asv-db" is not available.'
	exit 1
fi >&2

# shellcheck disable=SC1090
. <( grep '^POSTGRES_' "$topdir/.env" ) || exit 1

indata=$1

if [ -z "$1" ]; then
	echo 'Missing filename argument'
	exit 1
fi >&2

tmpdir=$(mktemp -d)

cleanup () { rm -f -r "$tmpdir"; }
trap cleanup INT TERM HUP

case $1 in
	*.csv)	# ok, we want CSV.
		cp "$1" "$tmpdir/data.csv"
		;;
	*.xlsx)	# ok, but need to convert to CSV.
		in2csv "$1" >"$tmpdir/data.csv"
		;;
	*)	# not ok, we got some strange filename.
		printf 'File has unknown filename suffix: %s\n' "$1" >&2
		echo 'Expected filename matching *.csv or *.xlsx' >&2
		exit 1
esac

indata=$tmpdir/data.csv

# ----------------------------------------------------------------------
# Verify that each sequence is already in the database.  Do this by
# calculating the MD5 checksums of the sequences in the CSV file, and
# then use these to query the database.
# ----------------------------------------------------------------------

# Get sequences, calculate ASV IDs, put these into an array.
readarray -t asv_ids < <(
	csvcut -c asv_sequence "$indata" |
	while IFS= read -r sequence; do
		asvhash "$sequence"
	done
)

# Get a list of any ASV IDs in the annotation file that are not found in
# the database.
readarray -t bad_asv_ids < <(
	# This bit extracts the IDs that do not exist in the database.
	# It uses a modified query from
	# https://dba.stackexchange.com/a/141137
	cat <<-END_SQL | do_dbquery
		WITH v (id) AS (
		VALUES
		$( printf "\t('%s'),\n" "${asv_ids[@]}" | sed '$s/,$//' )
		)
		SELECT v.id
		FROM v
		LEFT JOIN asv ON (asv.asv_id = v.id)
		WHERE asv.asv_id IS NULL
	END_SQL
)

# Delete the bad IDs from the array of IDs.
for bad_id in "${bad_asv_ids[@]}"; do
	printf 'WARNING: ASV ID "%s" not found in database\n' "$bad_id"
	for i in "${!asv_ids[@]}"; do
		[ "${asv_ids[i]}" != "$bad_id" ] && continue
		unset 'asv_ids[i]'
		break
	done
done

printf '%s\n' "${asv_ids[@]}"
cleanup
