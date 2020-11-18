
# variables
DIR="misc"
BASE="db-dump"
TIMESTAMP=$(date +"%Y-%m-%d_%H%M")
CONTAINER="asv-db"
FORMAT="tar" # change to 'plain' for plain SQL

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
  # a bunch of items in the dump are created by the maria.prager and postgres
  # roles, so we don't restore access privileges for now.
  cat "$FILE" | docker exec -i "${CONTAINER}" pg_restore \
    --no-acl \
    --no-owner \
    $FLAGS
else
    if [[ "$1" == "schema" ]]
    then
      FILE="${FILE%.*}-schema.sql"
      FLAGS="$FLAGS --schema-only"
    fi
    docker exec -i "${CONTAINER}" pg_dump \
    $FLAGS \
    --format=tar \
    -n "$PGRST_DB_SCHEMA" > "$FILE.$FORMAT"
fi
