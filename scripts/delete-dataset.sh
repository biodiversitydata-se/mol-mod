#!/bin/bash

topdir=$( readlink -f "$( dirname "$0" )/.." )

if [ ! -t 1 ]; then
	echo 'This script is supposed to be run interactively.'
	exit 1
fi >&2

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
*************************************
*** This script deletes datasets.
*** Use with care.
*************************************

MESSAGE_END
tput sgr0

do_dbquery () {
	docker exec asv-db \
	psql -h localhost -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
		--quiet --csv \
		-c "$1"
}

printf -v PS3fmt '%s' \
	'\n' \
	'Please select dataset to delete (2-%d),\n' \
	'or select 1 to quit.\n' \
	'--> '

while true; do
	readarray -t datasets < <( do_dbquery 'SELECT dataset_id FROM dataset' | sed 1d )
	nsets=${#datasets[@]}

	# shellcheck disable=SC2059
	printf -v PS3 "$PS3fmt" "$(( nsets + 1 ))"

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

	printf 'DELETING "%s"...\n' "$dataset"
	do_dbquery 'DELETE FROM dataset WHERE dataset_id = '"'$dataset'"
	echo 'Done.'
done
