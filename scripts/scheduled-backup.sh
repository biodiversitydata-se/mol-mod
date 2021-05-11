#!/bin/sh

#-----------------------------------------------------------------------
# This script will:
#
#	1.  Perform a database dump using the
#	    "$topdir/scripts/database-backup.sh" script, unless given
#	    the "-n" command line option.  This writes a compressed dump
#	    file to the "$topdir/db-backup" directory.
#
#	2.  Pull logs from the three Docker containers asv-main,
#	    asv-db, and asv-rest.  These logs are stored in
#	    "$topdir/log-backup".  Only the logging data produced since
#	    the last time this script ran will be stored (empty log
#	    backups are removed).  The timestamp on the symbolic link
#	    "$topdir/backups/latest" (which is re-created at the end of
#	    this script) is used to determine from when logs are to be
#	    stored.
#
#	3.  Perform an incremental backup of the following directories
#	    using rsync:
#
#		* "$topdir"/db-backup"	(the database backups)
#		* "$topdir/log-backup"	(the log backups)
#		* "asv-main:/uploads"	(the in-container upload directory)
#
#	The "$topdir" directory is the directory into which the mol-mod
#	Github reposiory has been cloned.  This will be found via this
#	script's location if the variable is left unset below.
#
#	Backups are written to "$topdir/backups/backup-{timestamp}",
#	where "{timestamp}" is a timestamp on the "YYYYMMDD-HHMMSS"
#	format.	 There will also be a symbolic link at "backups/latest",
#	which will point to the most recent backup directory.
#
#	Backups are incremental.  Unchanged files are hard-linked in
#	older backups and will not consume extra space.
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

if ! command -v rsync >/dev/null 2>&1
then
	echo 'rsync is not available, or not in PATH' >&2
	exit 1
fi >&2

unset topdir
topdir=$( readlink -f "${topdir:-"$( dirname "$0" )/.."}" )

backup_dir=$topdir/backups

case $backup_dir in
	([!/]*)
		# not an absolute path
		printf '"%s" is not an absolute pathname\n' "$backup_dir"
		exit 1
esac >&2

if [ ! -d "$backup_dir" ]; then
	printf 'Creating missing backup directory "%s"...\n' "$backup_dir"
	if ! mkdir "$backup_dir"; then
		echo 'Failed'
		exit 1
	fi
fi >&2

#-----------------------------------------------------------------------
# 1.  Do database dump.
#-----------------------------------------------------------------------

now=$(date +%Y%m%d-%H%M%S)
target_dir=$backup_dir/backup-$now

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

# Default options for "docker logs".
set -- --timestamps --details

if [ -d "$backup_dir/latest" ]; then
	set -- "$@" --since "$(stat --format %Z "$backup_dir/latest")"
fi

mkdir -p "$topdir/log-backup"
for container in asv-main asv-db asv-rest; do
	backup_file=$topdir/log-backup/$container.log.$now

	docker logs "$@" "$container" >"$backup_file" 2>&1

	# Remove log if nothing was logged since last backup.
	if [ ! -s "$backup_file" ]; then
		rm -f "$backup_file"
	fi
done

#-----------------------------------------------------------------------
# 3.  Do incremental backup of database dumps, log dumps, and the
#     "uploads" directory in the asv-main container.
#-----------------------------------------------------------------------

# Default rsync options.
set -- --archive --omit-dir-times --rsh='docker exec -i'

# Be quiet if we're running non-interatively
if [ -t 1 ] || "$be_verbose"; then
	set -- "$@" --itemize-changes
else
	set -- "$@" --quiet
fi

if "$be_verbose"; then
	set -- "$@" --verbose
fi

# Add --link-dest option if "$backup_dir/latest" exists.
if [ -d "$backup_dir/latest" ]; then
	set -- "$@" --link-dest="$backup_dir/latest/"
fi

# Note: No slash at the end of pathnames here.
for source_dir in "$topdir/db-backup" asv-main:/uploads "$topdir/log-backup"
do
	rsync "$@" "$source_dir" "$target_dir"
done

# (Re-)create "$backup_dir/latest" symbolic link.
rm -f "$backup_dir/latest"
ln -s "$(basename "$target_dir")" "$backup_dir/latest"
