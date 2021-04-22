#!/usr/bin/env python3
"""
This script updates `in_bioatlas` status for a dataset and/or updates the
materialized view used for summary stats in the About page. It is executed
inside a running asv-main container using the update_bas_status.py wrapper.
"""

import logging
import sys

import psycopg2
from importer import connect_db


def run_update(pid: int = 0, status: int = 1, dry_run: bool = False):
    '''Updates `in_bioatlas` status for a dataset, and/or updates the
       materialized db view that summarizes data for datasets that have been
       imported into the Bioatlas (i.e. have status `in_bioatlas = True)'''

    logging.info("Connecting to database")
    connection, cursor = connect_db()

    # If first argument in update_bas_status cmd is zero,
    # skip status update and only run the view update
    if pid > 0:
        # Translate status from int (simpler to write) to bool (used in db)
        if status == 0:
            status = False
        else:
            status = True
        try:
            logging.info("Updating Bioatlas status")
            cursor.execute(f"UPDATE dataset SET in_bioatlas = {status} \
                             WHERE pid = {pid};")
        except psycopg2.OperationalError as err:
            logging.error("Could not update Bioatlas status")
            logging.error(err)
            sys.exit(1)

    # Update view so that About page shows correct summary stats
    try:
        logging.info("Updating stats for About page")
        cursor.execute("REFRESH MATERIALIZED VIEW api.app_about_stats;")
    except psycopg2.OperationalError as err:
        logging.error("Could not update materialized view")
        logging.error(err)
        sys.exit(1)

    #
    # Commit or Roll back
    #

    if dry_run:
        logging.info("Dry run, rolling back changes")
        connection.rollback()
    else:
        logging.info("Committing changes")
        connection.commit()


if __name__ == '__main__':

    import argparse

    PARSER = argparse.ArgumentParser(description=__doc__)

    PARSER.add_argument('pid', type=int,
                        help=("pid of dataset to be status-updated,"
                              " or 0 for no dataset (i.e. view-update only)"))
    PARSER.add_argument('status', type=int,
                        help=("in_bioatlas value to be set: 0=False, 1=True"))
    PARSER.add_argument('--dry-run', action='store_true',
                        help=("Performs all transactions, but then issues a "
                              "rollback to the database so that it remains "
                              "unaffected. This will still increment "
                              "id sequences."))
    PARSER.add_argument('-v', '--verbose', action="count", default=0,
                        help="Increase logging verbosity (default: warning).")
    PARSER.add_argument('-q', '--quiet', action="count", default=3,
                        help="Decrease logging verbosity (default: warning).")

    ARGS = PARSER.parse_args()

    # Set log level based on ./scripts/import_excel argument
    # E.g: --v means log level = 10(3-2) = 10
    logging.basicConfig(level=(10*(ARGS.quiet - ARGS.verbose)))
    run_update(ARGS.pid, ARGS.status, ARGS.dry_run)
