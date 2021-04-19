#!/bin/sh
# This script runs during database initialization,
# i.e. when asv-db is started with postgres-data dir removed,
# or if executed inside running asv-db container (See README.md) with DBACCESS argument
# Adds db access (via 5432) to all IP:s listed in DBACCESS variable, in .env file

if [ -n "$DBACCESS" ]; then
  for hostaccess in $DBACCESS; do
    echo "Adding $hostaccess to allowed IP:s"
    sed -i -e '/all\s\s*all\s\s*all\s\s*/ d' "$PGDATA/pg_hba.conf"
    echo "host all all $hostaccess ${POSTGRES_HOST_AUTH_METHOD:-md5}" >> "$PGDATA/pg_hba.conf"
  done
  echo "host all all all reject" >> "$PGDATA/pg_hba.conf"
fi
