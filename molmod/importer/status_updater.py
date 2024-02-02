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


def run_update(pid: int = 0, status: int = None, ruid: str = None,
               ipt: str = None, dry_run: bool = False):
    """Updates dataset metadata and/or materialized db view that summarizes
       data for datasets that are currently used in the Bioatlas.
    """

    logging.info("Connecting to database")
    connection, cursor = connect_db()

    # Update Bioatlas metadata for the referenced dataset, if any
    if pid > 0:
        update_columns = []

        if status is not None:
            update_columns.append(f"in_bioatlas = {bool(status)}")

        if ruid is not None:
            update_columns.append(f"bioatlas_resource_uid = '{ruid}'")

        if ipt is not None:
            update_columns.append(f"ipt_resource_id = '{ipt}'")

        if update_columns:
            update_columns_str = ', '.join(update_columns)
            sql = f"UPDATE dataset SET {update_columns_str} WHERE pid = {pid};"
            # print(cursor.mogrify(sql))
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
    PARSER.add_argument('--status', nargs='?', type=int,
                        help="in_bioatlas value to be set: 0=False, 1=True")
    PARSER.add_argument('--ruid', nargs='?', type=str,
                        help="bioatlas_resource_uid value to be set, "
                             "e.g. 'dr10'")
    PARSER.add_argument('--ipt', nargs='?', type=str,
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

    # Set log level based on the -v and -q args added to the wrapper command
    # E.g: -v means log level = 10(3-1) = 20 = INFO
    # E.g: -vv means log level = 10(3-2) = 10 = DEBUG
    # E.g: -qqvv means log level = 10(5-2) = 30 = WARNING
    logging.basicConfig(level=(10*(ARGS.quiet - ARGS.verbose)))

    run_update(ARGS.pid, ARGS.status, ARGS.ruid, ARGS.ipt, ARGS.dry_run)
