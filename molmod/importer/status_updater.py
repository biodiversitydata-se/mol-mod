#!/usr/bin/env python3
"""
This script updates 'in_bioatlas status' and 'bioatlas_resource_uid' for a
dataset and/or updates the materialized view used for summary stats in the
About page. It is executed inside a running asv-main container using the
update_bas_status.py wrapper.

Note that we save data with a new 'dataset_id' if users provide a
corrected version of their dataset. Old and new datasets will then have
identical 'bioatlas_resource_uid' in our db, but only one of them should
have 'in_bioatlas' status = True at any point in time.

In contrast, we will not set a new 'dataset_id' when we perform a
regular re-annotation of data, but instead save all annotations and
flag them as having 'status' old or valid.
"""

import logging
import sys

import psycopg2
from importer import connect_db


def run_update(pid: int = 0, status: int = 1, ruid: str = '',
               dry_run: bool = False):
    """Updates 'in_bioatlas status' and 'bioatlas_resource_uid' for a dataset,
       and/or updates the materialized db view that summarizes data for
       datasets that are currently used in the Bioatlas.
       """

    logging.info("Connecting to database")
    connection, cursor = connect_db()

    # Update Bioatlas metadata for the referenced dataset, if any
    if pid > 0:
        # Update ruid if it has been supplied, otherwise keep it
        if ruid:
            sql = f"UPDATE dataset SET in_bioatlas = {bool(status)}, \
                   bioatlas_resource_uid = '{ruid}' \
                   WHERE pid = {pid};"
        else:
            sql = f"UPDATE dataset SET in_bioatlas = {bool(status)} \
                   WHERE pid = {pid};"
        try:
            logging.info("Updating Bioatlas status")
            cursor.execute(sql)
        except psycopg2.OperationalError as err:
            logging.error("Could not update Bioatlas status")
            logging.error(err)
            sys.exit(1)

    # Update materialized views
    # About stats
    try:
        logging.info("Updating stats for About page")
        cursor.execute("REFRESH MATERIALIZED VIEW api.app_about_stats;")
    except psycopg2.OperationalError as err:
        logging.error(err)
        sys.exit(1)
    # Filter dropdowns
    try:
        logging.info("Updating data for filter dropdown options")
        cursor.execute("REFRESH MATERIALIZED VIEW api.app_filter_mixs_tax;")
    except psycopg2.OperationalError as err:
        logging.error(err)
        sys.exit(1)
    # Filter results
    try:
        logging.info("Updating data for filter search results")
        cursor.execute("REFRESH MATERIALIZED VIEW api.app_search_mixs_tax;")
    except psycopg2.OperationalError as err:
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

    PARSER.add_argument('--pid', type=int, default=0,
                        help="pid of dataset to be status-updated,"
                             " or 0 for no dataset (i.e. view-update only)")
    PARSER.add_argument('--status', type=int, default=1,
                        help="in_bioatlas value to be set: 0=False, 1=True")
    PARSER.add_argument('--ruid', type=str, default="",
                        help="bioatlas_resource_uid value to be set, "
                             "e.g. 'dr10'")
    PARSER.add_argument('--dry-run', action='store_true',
                        help="Performs all transactions, but then issues a "
                             "rollback to the database so that it remains "
                             "unaffected. This will still increment "
                             "id sequences.")
    PARSER.add_argument('-v', '--verbose', action="count", default=0,
                        help="Increase logging verbosity (default: warning).")
    PARSER.add_argument('-q', '--quiet', action="count", default=3,
                        help="Decrease logging verbosity (default: warning).")

    ARGS = PARSER.parse_args()

    # Set log level based on ./scripts/import_excel argument
    # E.g: --v means log level = 10(3-2) = 10
    logging.basicConfig(level=(10*(ARGS.quiet - ARGS.verbose)))

    run_update(ARGS.pid, ARGS.status, ARGS.ruid, ARGS.dry_run)
