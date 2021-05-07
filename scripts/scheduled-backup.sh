#!/bin/sh

#-----------------------------------------------------------------------
# This script will:
#
#	1.  Perform a database dump using the
#	    "scripts/database-backup.sh" script, unless given the "-n"
#	    command line option.
#
#	2.  Perform an incremental backup of the following directories
#	    using rsync:
#
#		* "$toplevel"/db	(the database backups)
#		* asv-main:/upload	(the in-container upload directory)
#
#	The "$toplevel" directory is the directory into which the
#	mol-mod Github reposiory has been cloned, and this will be found
#	via this script's location if the variable is left unset below.
#
#	Backups are written to "$toplevel/backups/backup-timestamp"
#	where "timestamp" is a timestamp on the YYYYMMDD-HHMMSS format.
#	There will also be a symbolic link, "$toplevel/backups/latest",
#	which will point to the most recent backup.
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

unset toplevel

if ! command -v rsync >/dev/null 2>&1
then
	echo 'rsync is not available, or not in PATH' >&2
	exit 1
fi

toplevel=$( readlink -f "${toplevel:-"$( dirname "$0" )/.."}" )

backup_dir=$toplevel/backups

case $backup_dir in
	/*)	# absolute path, okay
		;;
	*)	# not an absolute path
		printf '"%s" is not an absolute pathname\n' "$backup_dir" >&2
		exit 1
esac

if [ ! -d "$backup_dir" ]; then
	printf 'Creating "%s"...\n' "$backup_dir"
	if ! mkdir "$backup_dir"; then
		echo 'Failed'
		exit 1
	fi
fi >&2

target_dir=$backup_dir/backup-$(date +%Y%m%d-%H%M%S)

# Default rsync options.
set -- --archive --itemize-changes -e 'docker exec -i'

# Add --link-dest option if "$backup_dir/latest" exists.
if [ -d "$backup_dir/latest" ]; then
	set -- "$@" --link-dest="$backup_dir/latest/"
fi

# Note: No slash at the end of pathnames here.
for source_dir in "$toplevel/db" asv-main:/uploads; do
	rsync "$@" "$source_dir" "$target_dir"
done

# (Re-)create "$backup_dir/latest" symbolic link.
rm -f "$backup_dir/latest"
ln -s "$(basename "$target_dir")" "$backup_dir/latest"
