#!/usr/bin/env python3
"""
The data exporter reads data from event-core-like views in the database,
saves these as tsv files in dataset folders, which are then zipped up and
compressed. The script is executed inside a running asv-main container, using
the export_archive.py wrapper.
"""

import logging
import os
import requests
import shutil
import sys
import time

import psycopg2
from psycopg2.extras import DictCursor


def connect_db(pass_file: str = '/run/secrets/postgres_pass'):
    """
    Uses environment variables to set up a database connection. A simple
    query to list datasets is then used to verify the connection.
    """
    try:
        with open(pass_file) as password:
            password = password.read()
    except FileNotFoundError:
        logging.error("Could not read postgres pwd from %s", pass_file)
        sys.exit(1)

    try:
        connection = psycopg2.connect(
            user=os.getenv('POSTGRES_USER', 'psql'),
            password=password,
            database=os.getenv('POSTGRES_DB', 'db'),
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=os.getenv('POSTGRES_PORT', '5432')
        )
        logging.info("Connected to PostgreSQL database")
        cursor = connection.cursor(cursor_factory=DictCursor)

        cursor.execute("SELECT * FROM public.dataset;")
        logging.debug("Database connection verified")
    except psycopg2.OperationalError as err:
        logging.error("Could not connect to postgres database")
        logging.error(err)
        sys.exit(1)
    return connection, cursor


def get_ds_meta(cursor, pid):
    """
    Retrieves dataset_id corresponding to any provided dataset.pid argument.
    """
    sql = ("SELECT dataset_id, ipt_resource_id FROM dataset "
           f"WHERE dataset.pid = {pid}")
    cursor.execute(sql)
    result = cursor.fetchone()
    if result is None:
        logging.error(f"No dataset found for pid {pid}")
        return None, None
    else:
        dataset_id, ipt_resource_id = result
        if ipt_resource_id is None:
            logging.error(f"No ipt_resource_id found for pid {pid}")
            return None, None
        return dataset_id, ipt_resource_id


def get_eml_file(ipt_resource_id, dir):
    """
    Downloads dataset metadata (eml.xlm file) from a given IPT resource,
    and saves this to a given directory.
    """
    ipt_base_url = os.getenv('IPT_BASE_URL')
    url = f'{ipt_base_url}/eml.do?r={ipt_resource_id}'
    destination_path = os.path.join(dir, 'eml.xml')

    # Simulate failure
    # url = "https://httpbin.org/status/404"
    # url = "https://httpbin.org/status/503"
    response = requests.get(url)
    if response.status_code == 200:
        with open(destination_path, 'wb') as file:
            file.write(response.content)
        return True
    else:
        logging.error("Failed to download eml file. Status code: "
                      f"{response.status_code}")
        return False


def export_datasets(pids: str):
    """
    Saves tsv data from a set of db views in database folders, which are then
    zipped up and ccompressed.
    """
    _, cursor = connect_db()

    if pids:
        pid_lst = pids.split()
    else:
        # If no dataset is provided, export all datasets
        sql = "SELECT pid FROM dataset WHERE in_bioatlas = TRUE"
        cursor.execute(sql)
        pid_lst = [str(row[0]) for row in cursor.fetchall()]

    for pid in pid_lst:
        start_time = time.time()
        id, ipt_resource_id = get_ds_meta(cursor, pid)
        if id is None:
            continue
        logging.info("Exporting dataset: %s", id)
        dir = os.path.join('/app/exports', id)
        os.makedirs(dir, exist_ok=True)

        # Get metadata file from IPT
        if not get_eml_file(ipt_resource_id, dir):
            shutil.rmtree(dir, ignore_errors=True)
            continue
        # Get data from db
        try:
            for view in ['event', 'emof', 'occurrence', 'asv']:
                tsv_path = os.path.join(dir, f"{view}.tsv")
                with open(tsv_path, 'w') as tsv:
                    sql = (f"SELECT * FROM api.dl_{view} "
                           f"WHERE dataset_pid = {pid}")
                    cp = (f"COPY ({sql}) TO STDOUT "
                          f"WITH CSV DELIMITER E'\t' HEADER")
                    cursor.copy_expert(cp, tsv)
            shutil.make_archive(dir, 'zip', dir)
            shutil.rmtree(dir)

            elapsed_time = time.time() - start_time
            logging.info("Time required: %.2f seconds", elapsed_time)
        except Exception as e:
            logging.error(f"Error exporting dataset {id}: {e}")

    cursor.close()


if __name__ == '__main__':

    import argparse

    PARSER = argparse.ArgumentParser(description=__doc__)

    PARSER.add_argument('--ds', default='', type=str,
                        help="List of datasets to export, space-separated.")
    PARSER.add_argument('-v', '--verbose', action="count", default=0,
                        help="Increase logging verbosity (default: warning).")
    PARSER.add_argument('-q', '--quiet', action="count", default=3,
                        help="Decrease logging verbosity (default: warning).")

    ARGS = PARSER.parse_args()

    # Set log level based on ./scripts/import_excel argument (se also Makefile)
    # E.g: -vv means log level = 10(3-2) = 10
    logging.basicConfig(level=(10*(ARGS.quiet - ARGS.verbose)))

    export_datasets(ARGS.ds)
