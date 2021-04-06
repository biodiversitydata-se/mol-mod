#!/usr/bin/env bash

# This script can be used to back up or restore postgres data (and schemas),
# by executing pg_dump / pg_restore inside a running asv-db container.
#
# When the container starts up, schemas and data are loaded from a bind-mounted
# folder or named volume (see docker-compose files). If these are empty,
# db schemas are created from the db_[api/data]_schema.sql files,
# requiring data to be restored with this script, together with a dump
# produced with 'data' option.

DIR=misc
BASE=db-dump
TIMESTAMP=$(date +"%Y-%m-%d_%H%M")
CONTAINER=asv-db
FORMAT=tar	# Change to 'plain' for plain SQL

#
# CREATE HELP (access with './backup.sh -h' in molmod folder)
#
if [ "$1" = -h ] || [ "$1" = --help ]; then
  cat <<'HELP'
USAGE: ./backup.sh [restore [filename] | data]

Given no arguments, this script will use the variables in .env to create a
database backup.

Viable options are:

      restore <file>    restore the named database dump, or the latest database
                        dump if no filename is given. The latest dump is
                        selected by modification date, not from the filename.

      data              make a backup containing only the public table data.

HELP
  exit
fi

if [ "$( docker container inspect -f '{{.State.Status}}' "$CONTAINER" )" != running ]
then
  echo 'Database container need to be running to perform backup operations' >&2
  exit 1
fi

# Load database variables
source .env

FILE=$DIR/${BASE}_$TIMESTAMP.sql
FLAGS=( -h localhost -U "$POSTGRES_USER" -d "$POSTGRES_DB" )

#
# RESTORE DB
#
if [ "$1" = "restore" ]; then
  # If no file is specified, use latest dump
  if [ -z "$2" ]; then
    # Get files matching pattern
    FILES=$(find "$DIR" -name "$BASE*")
    # Save in time-sorted array
    SORTED=($(echo $FILES | xargs ls -t))
    # Get latest modified file
    FILE=${SORTED[0]}

  # Otherwise use specified dump
  elif [ -f "$2" ]; then 
    FILE=$2
  else
    FILE=$DIR/$2
  fi

  # If no dumps are found, quit
  if [ ! -e "$FILE" ]; then
    printf 'Could not find database dump file "%s"\n' "$FILE" >&2
    exit 1
  fi

  # Restore
  printf 'Restoring database from dumps file "%s"\n' "$FILE"
  docker exec -i "${CONTAINER}" pg_restore "${FLAGS[@]}" <"$FILE"

#
# BACKUP DB
#
else
  # If 'data' arg is given, dump data (from schema public) only,
  # to produce file that can be used with `restore` option later
  # Otherwise schema api (views and functions, no data) are dumped
  if [ "$1" = data ]; then
    FILE=$DIR/$BASE-data_$TIMESTAMP.sql
    FLAGS+=( -n public --data-only )
  fi

  printf 'Creating database dump file "%s"\n' "$FILE"
  docker exec -i "$CONTAINER" \
    pg_dump "${FLAGS[@]}" --format="$FORMAT" \
    -n "$PGRST_DB_SCHEMA" >"$FILE.$FORMAT"
fi
