#!/bin/sh

#-----------------------------------------------------------------------
# This script will:
#
#	1.  Write a compressed database dump to "$backup_dir/db" using
#	    "$topdir/scripts/database-backup.sh" script, unless given
#	    the "-n" command line option.
#
#	2.  Pull data from Docker container logs and store these in
#	    "$backup_dir/logs". Only the logging data produced since
#	    the last time this script ran will be pulled (empty log
#	    backups are removed). The timestamp on the (empty) latest_backups_*
#	    file (which is re-created at the end of this script) is used to
#	    determine from when logs are to be stored.
#
#	3.  Copy newly uploaded dataset files from Docker container to host
#	    directory "$backup_dir/uploads".
#
#	The "$topdir" directory is the directory into which the mol-mod
#	Github reposiory has been cloned. This will be found via this
#	script's location.
#
#	This script is suitable to be run from crontab.	 Suggested
#	crontab entry for twice-daily backups as 9 AM and 9 PM:
#
#		0 9,21 * * * /opt/mol-mod/scripts/scheduled-backup.sh
#-----------------------------------------------------------------------

usage () {
	cat <<-END_USAGE
	Usage:

	    $0 -h

	    $0 [-n] [-v]

	Options:

	    -h	displays this help text
	    -n	do not dump database
	    -v	be more verbose

	END_USAGE
}

#-----------------------------------------------------------------------
# Do command line parsing.
#-----------------------------------------------------------------------

be_verbose=false
do_db_dump=true

while getopts 'hnv' opt; do
	case $opt in
		h)
			usage
			exit
			;;
		n)
			do_db_dump=false
			;;
		v)
			be_verbose=true
			;;
		*)
			echo 'Error in command line parsing' >&2
			usage >&2
			exit 1
	esac
done

shift "$(( OPTIND - 1 ))"

#-----------------------------------------------------------------------
# Sanity checking our environment before starting.
#-----------------------------------------------------------------------

# Only run if the "asv-main" container is running.
if [ "$( docker container inspect -f '{{ .State.Running }}' asv-main )" != 'true' ]
then
	echo 'Container "asv-main" not available'
	exit 1
fi >&2

topdir=$( readlink -f "$( dirname "$0" )/.." )
backup_dir=$topdir/backups

case $backup_dir in
	([!/]*)
		# not an absolute path
		printf '"%s" is not an absolute pathname\n' "$backup_dir"
		exit 1
esac >&2

if [ ! -d "$backup_dir" ]; then
    printf 'Creating missing backup directory "%s"\n' "$backup_dir"
    if ! mkdir -p "$backup_dir"; then
        exit 1
    fi
fi >&2

if [ ! -d "$backup_dir" ]; then
	printf 'Creating missing backup directory "%s"\n' "$backup_dir"
	if ! mkdir -p "$backup_dir"; then
		exit 1
	fi
fi >&2

for dir in db logs uploads; do
	if ! mkdir -p backups/"$dir"; then
		exit 1
	fi
done

#-----------------------------------------------------------------------
# 1.  Do database dump.
#-----------------------------------------------------------------------

if "$do_db_dump"; then
	FORMAT=custom "$topdir"/scripts/database-backup.sh data |
	if [ -t 1 ] || "$be_verbose"; then
		cat
	else
		cat >/dev/null
	fi
fi

#-----------------------------------------------------------------------
# 2.  Do Docker log dump.
#-----------------------------------------------------------------------

now=$(date +%Y%m%d-%H%M%S)

set -- --timestamps --details

latest=$(find "$backup_dir" -maxdepth 1 -type f -name 'latest_backup*' -print -quit)

if [ -n "$latest" ]; then
    latest_timestamp=$(stat --format %Z "$latest")
    set -- "$@" --since "$latest_timestamp"
fi

containers=$(docker compose ps | awk 'NR>1 { print $1 }')
for container in $containers; do
	backup_file=$backup_dir/logs/$container.log.$now

	docker logs "$@" "$container" >"$backup_file" 2>&1

	# e.g. 'docker logs --timestamps --details --since 1692955416 asv-main > ...'
	# which pulls entries since 2023-08-25T09:23:36.399165925Z (in UTC time;
	# log entries also have local time added via log_config)

	# Remove log if nothing was logged since last backup.
	if [ ! -s "$backup_file" ]; then
		rm -f "$backup_file"
	else
		printf '* Adding log increment: %s\n' "$container.log.$now"
	fi

done

#-----------------------------------------------------------------------
# 3.  Copy new uploads.
#-----------------------------------------------------------------------

# Copy new uploads
for file in $(docker exec asv-main ls /app/uploads); do
    if [ ! -e "$backup_dir/uploads/$file" ]; then
        echo "* Adding new upload: $file"
        docker cp "asv-main:/app/uploads/$file" "$backup_dir/uploads"
    fi
done

#-----------------------------------------------------------------------
# Finish up
#-----------------------------------------------------------------------

# Replace empty file used for timestamp and quick backup check
rm -f "$backup_dir/latest_backup"*
touch "$backup_dir/latest_backup_$now"
