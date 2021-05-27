#!/usr/bin/env bash

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

# Verify that each sequence is already in the database.  Do this by
# calculating the MD5 checksums of the sequences in the CSV file, and
# then use these to query the database.

readarray -t asv_ids < <(
	csvcut -c asv_sequence "$indata" |
	while IFS= read -r sequence; do
		asvhash "$sequence"
	done
)

query=$(cat <<-END_SQL
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

while IFS= read -r bad_asv_id; do
	printf 'WARNING: ASV ID "%s" not found in database\n' "$bad_asv_id"
	for i in "${!asv_ids[@]}"; do
		if [ "${asv_ids[i]}" = "$bad_asv_id" ]; then
			unset 'asv_ids[i]'
			break
		fi
	done
done < <( do_dbquery "$query" )

printf '%s\n' "${asv_ids[@]}"
cleanup
