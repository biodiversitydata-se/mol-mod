#!/usr/bin/env python3
"""
This script is executed inside a running asv-main container, using the
export_data.py wrapper. Depending on arguments added to the wrapper,
the exporter either reads data from event-core-like DwC views and produces
condensed dataset archives, or exports fasta files to be used in taxonomic
reannotation.
"""

import logging
import os
import requests
import shutil
import sys
import time
from datetime import datetime as dt

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


def get_dataset_ids(cursor, pid):
    """
    Retrieves dataset ID values (i.e. datasetID, drXXX and IPT resource)
    corresponding to a provided pid (pk, integer) value.
    """
    sql = ("SELECT dataset_id, ipt_resource_id, bioatlas_resource_uid "
           f"FROM dataset WHERE dataset.pid = {pid}")
    cursor.execute(sql)
    result = cursor.fetchone()
    if result is None:
        logging.error(f"No dataset found for pid {pid}")
        return None, None, None
    else:
        dataset_id, ipt_id, bioatlas_id = result
        if ipt_id is None:
            logging.error(f"No ipt_resource_id found for pid {pid}")
            return None, None, None
        if bioatlas_id is None:
            logging.error(f"No bioatlas_resource_uid found for pid {pid}")
            return None, None, None
    return result


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


def make_readme(bioatlas_id, dir):
    """
    Requests key metadata values from Bioatlas API and adds these to template
    to create README in provided directory.
    """
    url = 'https://collections.biodiversitydata.se/ws/citations'
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json'
    }
    response = requests.post(url, headers=headers, json=[bioatlas_id])
    destination_path = os.path.join(dir, 'README.txt')

    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(script_dir, 'readme-template.txt')

    if response.status_code == 200:
        data = response.json()[0]
        if data is not None:
            with open(template_path, 'r', encoding='utf-8') as readme:
                template = readme.read()
            # Replace [API data] with metadata
            replacement = (
                f"Dataset name: {data['name']}\n"
                f"Citation: {data['citation']}\n"
                f"Rights: {data['rights']}\n"
                f"DOI: {data.get('DOI', '')}"
            )
            readme = template.replace('[API data]', replacement)
            with open(destination_path, 'w', encoding='utf-8') as file:
                file.write(readme)
            return True
        else:
            logging.error(f"No metadata found for {bioatlas_id}")
            return False
    else:
        logging.error(f"Bioatlas API request failed: {response.status_code}")
        return False


def export_datasets(pids: str):
    """
    Exports data and metadata for a list of / all datasets to compressed files.
    For each dataset, calls functions to get eml file from IPT, key metadata
    from Bioatlas API, and data from DB.
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
        dataset_id, ipt_id, bioatlas_id = get_dataset_ids(cursor, pid)
        if dataset_id is None:
            continue
        logging.info("Exporting dataset: %s", dataset_id)

        # Make clean dataset dir
        dir = os.path.join('/app/exports', dataset_id)
        if os.path.exists(dir):
            shutil.rmtree(dir, ignore_errors=True)
        os.makedirs(dir, exist_ok=True)

        # Get eml file from IPT
        if not get_eml_file(ipt_id, dir):
            shutil.rmtree(dir, ignore_errors=True)
            continue

        # Add key metadata from Bioatlas to readme
        if not make_readme(bioatlas_id, dir):
            shutil.rmtree(dir, ignore_errors=True)
            continue

        # Get data files from DB
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
            logging.error(f"Error exporting dataset {dataset_id}: {e}")

    cursor.close()


def create_output_fasta(ref: str = '', target: str = ''):
    """
    Creates a fasta file of all ASVs currently annotated with a specific
    (version of a) reference database, e.g. 'UNITE:8.0'.
    """

    _, cursor = connect_db()

    filename = 'export-' + dt.now().strftime("%y%m%d-%H%M%S")

    # Create the fasta file
    logging.info("Exporting fasta file: %s.fasta", filename)

    sql = f"SELECT DISTINCT(a.asv_id), a.asv_sequence \
           FROM public.taxon_annotation ta, public.asv a \
           WHERE a.pid = ta.asv_pid \
           AND split_part(reference_db, ' (', 1) = '{ref}' \
           AND split_part(annotation_target, ' (', 1) = '{target}';"

    dir = '/app/fasta-exports'
    if not os.path.exists(dir):
        os.makedirs(dir)
    with open(f'{dir}/{filename}.fasta', 'w') as fasta:
        cursor.execute(sql)
        for asv_id, sequence in cursor.fetchall():
            fasta.write('>%s\n%s\n' % (asv_id, sequence))


if __name__ == '__main__':

    import argparse

    PARSER = argparse.ArgumentParser(description=__doc__)

    PARSER.add_argument('--ds', default='', type=str,
                        help="List of datasets to export, space-separated.")
    PARSER.add_argument('--ref', default="",
                        help="Reference database for filtering of ASVs in"
                             "fasta export. Use to return all ASVs currently "
                             "annotated with a specific db.")
    PARSER.add_argument('--target', default="",
                        help="Target gene for filtering of ASVs in"
                             "fasta export. Use to return all ASVs derived "
                             "from a specific target gene.")
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
    # If a reference database is given, just export a fasta file
    if ARGS.ref or ARGS.target:
        create_output_fasta(ARGS.ref, ARGS.target)
    else:
        export_datasets(ARGS.ds)
