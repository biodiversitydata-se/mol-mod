#!/usr/bin/env bash
# This script can be used to back up or restore postgres data (and schemas),
# by executing pg_dump / pg_restore inside a running asv-db container.

# variables
DIR="misc"
BASE="db-dump"
TIMESTAMP=$(date +"%Y-%m-%d_%H%M")
CONTAINER="asv-db"
FORMAT="tar" # change to 'plain' for plain SQL

if [[ "$1" == "-h" ]] | [[ "$1" == "--help" ]]
then
  cat << HELP
USAGE: ./backup.sh [restore [filename] | data]

Given no arguments, this script will use the variables in .env to create a
database backup.

Viable options are:

      restore <file>    restore the named database dump, or the latest database
                        dump if no filename is given. The latest dump is
                        selected by modification date, not from the filename.

      data              make a backup containing only the public table data.

HELP
  exit 0
fi

if [ "$( docker container inspect -f '{{.State.Status}}' ${CONTAINER} )" != "running" ]
then
  echo "Database container need to be running to perform backup operations"
  exit 1
fi

# load database variables
source .env

FILE="${DIR}/${BASE}_${TIMESTAMP}.sql"
FLAGS="-h localhost -U $POSTGRES_USER -d $POSTGRES_DB"

if [[ "$1" == "restore" ]]
then
  if [[ "$2" == "" ]]
  then
    # get latest modified file matching the pattern
    FILES=$(find "$DIR" -name "$BASE*")
    # array of files sorted by time. Note that piping to ls has problems, as it
    # can't handle filenames with special characters (like whitespace).
    SORTED=($(echo $FILES | xargs ls -t))
    # Get the latest modified file from the array
    FILE=${SORTED[0]}
  else
    [ -f "$2" ] && FILE="$2" || FILE="$DIR/$2"
  fi

  if [ ! -e "${FILE}" ]
  then
    echo "Couldn't find database dump file '$FILE'." >&2
    exit 1
  fi
  echo "Restoring database from latest dump: ${FILE}"
  cat "$FILE" | docker exec -i "${CONTAINER}" pg_restore $FLAGS
else
    if [[ "$1" == "data" ]]
    then
      FILE="${DIR}/${BASE}-data_${TIMESTAMP}.sql"
      FLAGS="$FLAGS -n public --data-only"
    fi
    echo "Creating database dump ${FILE}"
    docker exec -i "${CONTAINER}" pg_dump \
    $FLAGS \
    --format="$FORMAT" \
    -n "$PGRST_DB_SCHEMA" > "$FILE.$FORMAT"
fi
