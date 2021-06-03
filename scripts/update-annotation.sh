#!/usr/bin/env bash

# Mapping of the data file's column names to database column names.
declare -A colname_map
colname_map=(
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

# Make readlink use GNU readlink on macOS.
readlink () {
	case $OSTYPE in
		linux*)
			command readlink "$@"
			;;
		*)
			command greadlink "$@"
	esac
}

# Simplifies making a query to the database in the asv-db container.
do_dbquery () {
        # Use --command if we got an argument.  Otherwise, read SQL
        # commands from standard input.

	if [ "$#" -ne 0 ]; then
		set -- --command="$*"
	fi

	docker exec -i asv-db \
		psql --host=localhost --user="$POSTGRES_USER" \
			--dbname="$POSTGRES_DB" \
			--no-align --echo-all --tuples-only "$@"
}

if ! command -v in2csv >/dev/null 2>&1; then
	cat <<-'END_MESSAGE'
		The command "in2csv" is not available.
		Please install the "csvkit" package,
		either using "pip install csvkit" or
		via a package manager.
	END_MESSAGE
	exit 1
fi >&2

topdir=$( readlink -f "$( dirname "$0" )/.." )

if [ ! -e "$topdir/.env" ]; then
	printf 'Can not see "%s" to read database configuration.\n' "$topdir/.env"
	exit 1
fi >&2

# Make sure that the needed containers are up and running.
for container in asv-db asv-main; do
	if [ "$( docker container inspect -f '{{ .State.Running }}' "$container" )" != 'true' ]
	then
		printf 'Container "%s" is not available.' "$container"
		exit 1
	fi >&2
done

# shellcheck disable=SC1090
. <( grep '^POSTGRES_' "$topdir/.env" ) || exit 1

printf -v connstr 'postgresql+psycopg2://%s:%s@%s:%s/%s' \
	"$POSTGRES_USER" \
	"$(<"$topdir/.secret.postgres_pass")" \
	"$POSTGRES_HOST" \
	"$POSTGRES_PORT" \
	"$POSTGRES_DB"

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

# Change the data file's column names.
if [[ $OSTYPE == linux* ]]; then
	ws='\<'
	we='\>'
else
	ws='[[:<:]]'
	we='[[:>:]]'
fi
cp "$indata" "$indata.tmp"
for colname in "${!colname_map[@]}"; do
	[ "$colname" = "${colname_map[$colname]}" ] && continue
	printf '1s/%s%s%s/%s/\n' "$ws" "$colname" "$we" "${colname_map[$colname]}"
done | sed -f /dev/stdin "$indata.tmp" >"$indata"

# Create a temporary table called "tmpdata".
cat <<-'END_SQL' | do_dbquery
	BEGIN;

	-- Drop old table if needed.
	DROP TABLE IF EXISTS tmpdata;

	-- Create the table with the same schema as "taxon_annotation",
	-- but with an additional "asv_sequence" column.
	CREATE TABLE tmpdata (
		LIKE taxon_annotation,
		asv_sequence CHARACTER VARYING
	 );

	-- Use the "pid" sequence from the "taxon_annotation" table,
	-- allow "asv_pid" to be NULL, and set the default "status"
	-- value to the string "valid".
	ALTER TABLE tmpdata
	ALTER COLUMN pid SET DEFAULT
		nextval('taxon_annotation_pid_seq'),
	ALTER COLUMN asv_pid DROP NOT NULL,
	ALTER COLUMN status SET DEFAULT 'valid';

	COMMIT;
END_SQL

# Load annotation data into "tmpdata" table.
docker exec -i asv-main \
	csvsql --db "$connstr" --insert --tables tmpdata \
		--no-create <"$indata"

cat <<-'END_SQL' | do_dbquery
	BEGIN;

	-- Populate the "asv_pid" column with the correct values based
	-- on the sequence data.
	UPDATE tmpdata AS t
	SET asv_pid = asv.pid
	FROM asv
	WHERE asv.asv_sequence = t.asv_sequence;

	-- As we're done with it, drop the "asv_sequence" column from
	-- our temporary table.
	ALTER TABLE tmpdata
	DROP COLUMN asv_sequence;

	-- Set the "status" of any existing annotation entries for these
	-- sequences to the string "old".
	UPDATE taxon_annotation AS ta
	SET status = 'old'
	FROM tmpdata AS t
	WHERE ta.asv_pid = t.asv_pid;

	-- Finally, copy the data from our temporary table into the
	-- annotation table.  Avoid inserting data associated with
	-- sequence data that couldn't be matched.
	INSERT INTO taxon_annotation
	SELECT * FROM tmpdata
	WHERE asv_pid IS NOT NULL;

	-- Drop the temporary table.
	DROP TABLE tmpdata;

	COMMIT;
END_SQL
