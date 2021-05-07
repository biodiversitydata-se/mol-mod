#!/bin/sh

#-----------------------------------------------------------------------
# This script will:
#
#	1.  Perform a database dump using the "scripts/backup.sh"
#	    script.
#
#	2.  Perform an incremental backup of the following directories
#	    using rsync:
#
#		* "$toplevel"/db
#		* "$toplevel"/log
#		* "$toplevel"/upload
#
#	The "$toplevel" directory is the director into which the mol-mod
#	Github reposiory has been checked out, and this will be found
#	via this script's location if the variable is left unset below.
#
#	Backups are written to "$toplevel/backup/backup-timestamp" where
#	"timestamp" is a timestamp on the YYYYMMDD-HHMMSS format.  There
#	will also be a symbolic link, "$toplevel/backup/latest", which
#	will point to the most recent backup.
#
#	Backups are incremental.  Unchanged files are hard-linked in
#	older backups.
#
#	This script is suitable to be run from crontab.	 Suggested
#	crontab entry for twice-daily backups as 9 AM and 9 PM:
#
#		0 9,21 * * * /opt/mol-mod/scripts/scheduled-backup.sh
#-----------------------------------------------------------------------

# TODO: Database dump

toplevel=

if ! command -v rsync >/dev/null 2>&1
then
	echo 'rsync is not available, or not in PATH' >&2
	exit 1
fi

toplevel=$( readlink -f "${toplevel:-"$( dirname "$0" )/.."}" )

backup_dir=$toplevel/backup

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

set --
if [ -d "$backup_dir/latest" ]; then
	set -- --link-dest="$backup_dir/latest/"
fi

for source_dir in db log upload; do
	source_dir=$toplevel/$source_dir

	if [ ! -d "$source_dir" ]; then
		printf 'Skipping "%s", directory not avaiable\n' "$source_dir"
		continue
	fi >&2

	rsync --archive --itemize-changes \
		"$@" \
		"$source_dir" "$target_dir"
done

rm -f "$backup_dir/latest"
ln -s "$(basename "$target_dir")" "$backup_dir/latest"
