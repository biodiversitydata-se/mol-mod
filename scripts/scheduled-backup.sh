#!/bin/sh

#-----------------------------------------------------------------------
# This script will:
#
#	1.  Perform a database dump using the
#	    "$topdir/scripts/database-backup.sh" script, unless given
#	    the "-n" command line option.
#
#	2.  Perform an incremental backup of the following directories
#	    using rsync:
#
#		* "$topdir"/db		(the database backups)
#		* "$container:/uploads"	(the in-container upload directory)
#
#	The "$topdir" directory is the directory into which the mol-mod
#	Github reposiory has been cloned.  This will be found via this
#	script's location if the variable is left unset below.
#
#	Backups are written to "backups/backup-{timestamp}" under
#	"$topdir", where "{timestamp}" is a timestamp on the
#	"YYYYMMDD-HHMMSS" format.  There will also be a symbolic link
#	at "backups/latest", which will point to the most recent backup
#	directory.
#
#	Backups are incremental.  Unchanged files are hard-linked in
#	older backups and will not consume extra space.
#
#	This script is suitable to be run from crontab.	 Suggested
#	crontab entry for twice-daily backups as 9 AM and 9 PM:
#
#		0 9,21 * * * /opt/mol-mod/scripts/scheduled-backup.sh
#-----------------------------------------------------------------------

# TODO: command line parsing
# TODO: Database dump

unset topdir
container=asv-main

# Only run if the "$container" container is running.
if [ "$( docker container inspect -f '{{ .State.Running }}' "$container" )" != 'true' ]
then
	printf 'Container "%s" not available\n'	"$container"
	exit 1
fi >&2

if ! command -v rsync >/dev/null 2>&1
then
	echo 'rsync is not available, or not in PATH' >&2
	exit 1
fi >&2

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

target_dir=$backup_dir/backup-$(date +%Y%m%d-%H%M%S)

# Default rsync options.
set -- --archive --rsh='docker exec -i'

# Be quiet if we're running non-interatively
if [ ! -t 1 ]; then
	set -- "$@" --quiet
else
	set -- "$@" --itemize-changes
fi

# Add --link-dest option if "$backup_dir/latest" exists.
if [ -d "$backup_dir/latest" ]; then
	set -- "$@" --link-dest="$backup_dir/latest/"
fi

# Note: No slash at the end of pathnames here.
for source_dir in "$topdir/db" "$container:/uploads"; do
	rsync "$@" "$source_dir" "$target_dir"
done

# (Re-)create "$backup_dir/latest" symbolic link.
rm -f "$backup_dir/latest"
ln -s "$(basename "$target_dir")" "$backup_dir/latest"
