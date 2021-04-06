#!/bin/sh

if [ -n "$DBACCESS" ]; then
  for hostaccess in $DBACCESS; do
    sed -i -e '/all\s\s*all\s\s*all\s\s*/ d' "$PGDATA/pg_hba.conf"
    echo "host all all $hostaccess ${POSTGRES_HOST_AUTH_METHOD:-md5}" >> "$PGDATA/pg_hba.conf"
  done
  echo "host all all all reject" >> "$PGDATA/pg_hba.conf"
fi

