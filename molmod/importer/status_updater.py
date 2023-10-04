#!/usr/bin/env python3
"""
This script updates dataset metadata and/or the materialized view used for
summary stats in the About page. It is executed inside a running asv-main
container using the update_bas_status.py wrapper.
"""

import logging
import sys

import psycopg2
from importer import connect_db


def run_update(pid: int = 0, status: int = 1, ruid: str = '',
               ipt: str = '', dry_run: bool = False):
    """Updates dataset metadata and/or materialized db view that summarizes
       data for datasets that are currently used in the Bioatlas.
       """

    logging.info("Connecting to database")
    connection, cursor = connect_db()

    # Update Bioatlas metadata for the referenced dataset, if any
    if pid > 0:
        update_columns = []

        # Check if 'in_bioatlas' status needs to be updated
        if status is not None:
            update_columns.append(f"in_bioatlas = {bool(status)}")

        # Check if 'bioatlas_resource_uid' needs to be updated
        if ruid:
            update_columns.append(f"bioatlas_resource_uid = '{ruid}'")

        # Check if 'ipt_resource_id' needs to be updated
        if ipt:
            update_columns.append(f"ipt_resource_id = '{ipt}'")

        # Construct the SQL query to update the specified columns
        if update_columns:
            update_columns_str = ', '.join(update_columns)
            sql = f"UPDATE dataset SET {update_columns_str} WHERE pid = {pid};"

            try:
                logging.info("Updating Bioatlas metadata")
                cursor.execute(sql)
            except psycopg2.OperationalError as err:
                logging.error("Could not update Bioatlas metadata")
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
    # Filter results
    try:
        logging.info("Updating data for filter search results")
        cursor.execute("REFRESH MATERIALIZED VIEW api.app_search_mixs_tax;")
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
    # Dataset table
    try:
        logging.info("Updating dataset table in Download data")
        cursor.execute("REFRESH MATERIALIZED VIEW api.app_dataset_list;")
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
    PARSER.add_argument('--ipt', type=str, default="",
                        help="ipt_resource_id value to be set, "
                             "e.g. 'kth-2013-baltic-18s'")
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
