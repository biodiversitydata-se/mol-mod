#!/usr/bin/env bash

# ======================================================================
# This script takes an annotation file as its only argument.  The file
# should be a Microsoft Excel spreadsheet (*.xlsx), or a corresponding
# CSV file (*.csv).
#
# The columns names in the file are expected to be the following (order
# is *not* important):
#
#	annotation_algorithm
#	annotation_confidence
#	class
#	date_identified
#	family
#	genus
#	identification_references
#	infraspecificEpithet
#	kingdom
#	order
#	otu
#	phylum
#	reference_db
#	scientificName
#	specificEpithet
#	taxonRank
#	taxon_remarks
#
# See the associative array "colname_map" below for how these are mapped
# to column names in the "taxon_annotation" table in the ASV database.
#
# The conversation with the database will be shown to the user, as a way
# of presenting the progress.
# ======================================================================

# ----------------------------------------------------------------------
# Setup and sanity checks.
# ----------------------------------------------------------------------

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

infile=$1

# Set up filter for data that produces CSV.
case $infile in
	*.csv)	# ok, we want CSV.
		filter=( cat )
		;;
	*.xlsx)	# ok, but need to convert to CSV.
		filter=( in2csv -f xlsx )
		;;
	*)	# not ok, we got some strange filename.
		printf 'File has unknown filename suffix: %s\n' "$infile" >&2
		echo 'Expected filename matching *.csv or *.xlsx' >&2
		exit 1
esac

# ----------------------------------------------------------------------
# Setup of the staging table in the database.
# ----------------------------------------------------------------------

# Create a temporary table called "tmpdata".
cat <<-'END_SQL' | do_dbquery
	-- We will now create the temporary table that will hold the
	-- data from the file.
	BEGIN;

	-- Drop old table if needed.
	-- This will generate a NOTICE if the table does not exist.
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
	-- Done.  The data will now be loaded using "csvsql" via the
	-- asv-main container.
END_SQL

# ----------------------------------------------------------------------
# Load annotation data into the "tmpdata" table using "csvsql" on the
# "asv-main" container, but first create CSV from the original data if
# needed and rename columns.
# ----------------------------------------------------------------------

# Create sed script to rename columns using the mapping in "colname_map".
unset colrename
for colname in "${!colname_map[@]}"; do
	[ "$colname" = "${colname_map[$colname]}" ] && continue
	colrename+=${colrename:+;}$(
		printf '1s/\<%s\>/%s/\n' "$colname" "${colname_map[$colname]}"
	)
done

docker exec -i asv-main sh -c '
	connstr=$1; shift
	colrename=$1; shift
	"$@" | sed -e "$colrename" |
	csvsql --db "$connstr" --insert --tables tmpdata --no-create' sh \
	"$connstr" "$colrename" "${filter[@]}" <"$infile"

# ----------------------------------------------------------------------
# Modify the data in the staging table and finally copy the data to the
# annotation table.
# ----------------------------------------------------------------------

cat <<-'END_SQL' | do_dbquery
	-- The data has now been loaded.  We now modify the data
	-- so that it's suitable to be copied straigt into the
	-- "taxon_annotation" table.
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

	-- "taxon_rank" should be blank rather than NULL.
	-- https://github.com/biodiversitydata-se/mol-mod/pull/51#issuecomment-855789302
	UPDATE tmpdata
	SET taxon_rank = ''
	WHERE taxon_rank IS NULL;

	-- Finally, copy the data from our temporary table into the
	-- annotation table.  Avoid inserting data associated with
	-- sequence data that couldn't be matched.
	INSERT INTO taxon_annotation
	SELECT * FROM tmpdata
	WHERE asv_pid IS NOT NULL;

	-- Delete the data that was copied.
	DELETE FROM tmpdata
	WHERE asv_pid IS NOT NULL;

	-- This is how many entries couldn't be used due to non-matching
	-- sequences.
	SELECT COUNT(*) FROM tmpdata;

	-- Drop the temporary table.
	DROP TABLE tmpdata;

	COMMIT;
	-- All done.
END_SQL
