#!/usr/bin/env bash

# This script presents the user with a menu showing the current datasets
# available in the PostgreSQL database running in the asv-db container.
# By selecting one of the datasets from the menu, that dataset and all
# associated data is deleted from the database.
#
# The script have no command line opitons and takes no other arguments.
#

readlink () {
	case $OSTYPE in
		linux*) command readlink "$@" ;;
		*) command greadlink "$@" ;;
	esac
}

topdir=$( readlink -f "$( dirname "$0" )/.." )

# Refuse to run non-interactively.
if [ ! -t 1 ]; then
	echo 'This script is supposed to be run interactively.'
	exit 1
fi >&2

#-----------------------------------------------------------------------
# Perform sanity checks and read database configuration.
#-----------------------------------------------------------------------

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

tput bold
cat <<'MESSAGE_END'
************************************************************************
		      This script deletes datasets
			     Use with care
************************************************************************

MESSAGE_END
tput sgr0

# Just a convinience function to send an SQL statement to the database.
# Initiates a separate session for each call.
do_dbquery () {
	docker exec asv-db \
	psql -h localhost -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
		--quiet --csv \
		-c "$1"
}

# Set up interactive prompt.
printf -v PS3fmt '%s' \
	'\n' \
	'Please select dataset to delete (2-%d),\n' \
	'or select 1 to quit.\n' \
	'--> '

#-----------------------------------------------------------------------
# Main menu loop.
#-----------------------------------------------------------------------

while true; do
	# Get list of current datasets.
	readarray -t datasets < <( do_dbquery 'SELECT dataset_id FROM dataset' | sed 1d )
	nsets=${#datasets[@]}

	# shellcheck disable=SC2059
	printf -v PS3 "$PS3fmt" "$(( nsets + 1 ))"

	# Show menu, get input, validate.
	select dataset in QUIT "${datasets[@]}"; do
		if [[ "$REPLY" != *[![:digit:]]* ]] && [ "$REPLY" -ne 0 ]; then
			if [ "$REPLY" -eq 1 ]; then
				break 2	# quit
			elif [ "$REPLY" -le "$(( nsets + 1 ))" ]
			then
				break	# other valid choice
			fi
		fi

		echo 'Invalid choice.' >&2
	done

	# Perform deletion.
	printf 'DELETING "%s"...\n' "$dataset"
	do_dbquery 'DELETE FROM dataset WHERE dataset_id = '"'$dataset'"
	do_dbquery 'DELETE FROM asv WHERE pid NOT IN (SELECT DISTINCT asv_pid FROM occurrence)'
	echo 'Done.'
done

echo 'Bye.'
