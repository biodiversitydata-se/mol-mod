#!/usr/bin/env python3
"""
This file contains functions for building a blast database from ASVs in
the postgres database, and for exporting fasta files for taxonomic reannotation
of all ASVs currently annotated with a specific (version of a) reference
database, e.g. 'UNITE:8.0'. The script is executed inside a running
blast-worker container using the build_blast_db.py wrapper.
"""

import logging
import os
import subprocess
import sys
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


def list_datasets_in_bioatlas(cursor: DictCursor) -> list:
    """
    Returns a list of all datasets available in the database where
    'in_bioatlas' is 'true'.
    """
    query = "SELECT pid, dataset_id FROM public.dataset \
             WHERE in_bioatlas;"

    cursor.execute(query)
    return [dict(row) for row in cursor.fetchall()]


def create_input_fasta(cursor: DictCursor, filename: str = 'blast_input'):
    """
    Uses the given database 'cursor' to extract sequences to be placed in
    'filename'.
    """
    logging.info("Creating input fasta file: %s.fasta", filename)

    with open(f'{filename}.fasta', 'w') as fasta:
        cursor.execute("SELECT * FROM api.app_asvs_for_blastdb;")
        for asv_id, taxonomy, sequence in cursor.fetchall():
            fasta.write('>%s-%s\n%s\n' % (asv_id, taxonomy, sequence))


def create_blast_db_from_fasta(fasta: str, db_name: str):
    """
    Creates a blast database 'db_name' from the sequences in  'fasta'.
    """
    logging.info("Creating blast database %s from %s", db_name, fasta)

    CMD = ['/blast/bin/makeblastdb', '-in', fasta, '-out', db_name, '-dbtype',
           'nucl']
    subprocess.call(CMD)


def create_blast_db(filename: str, db_dir: str = '.'):
    """
    Creates a blast database at 'db_dir'/'filename', made from all the datasets
    that have 'in_bioatlas' set to 'true'.
    """

    logging.info("Connecting to database")
    connection, cursor = connect_db()

    # Fetch all datasets that are to be added to the blast database. These are
    # only used to inform the user, the api.app_asvs_for_blastdb function
    # automatically returns sequences filtered by datasets in bioatlas.
    datasets = list_datasets_in_bioatlas(cursor)

    logging.info("Using datasets (pid/dataset_id): %s",
                 ', '.join([str(d['pid']) + "/" + d['dataset_id']
                            for d in datasets]))

    # Check input params:
    assert isinstance(filename, str), "Filename must be a string"
    assert len(filename) > 0, "Filename must be at least one character long"
    assert isinstance(db_dir, str), "Directory name must be a string"

    # Create filenames
    db_name = f'{os.path.join(db_dir, filename)}'
    fasta = f'{db_name}.fasta'

    # Update data used in blastdb build (and BLAST search)
    try:
        logging.info("Refreshing api.app_asvs_for_blastdb")
        cursor.execute("REFRESH MATERIALIZED VIEW api.app_asvs_for_blastdb;")
    except psycopg2.OperationalError as err:
        logging.error("Could not refresh materialized view")
        logging.error(err)
        sys.exit(1)

    # Create the fasta file
    create_input_fasta(cursor, db_name)

    # Create the blast database from the fasta
    create_blast_db_from_fasta(fasta, db_name)

    # and finally, remove the fasta file, as it's no longer needed
    os.remove(fasta)

    logging.info("Committing update of api.app_asvs_for_blastdb")
    connection.commit()


def create_output_fasta(ref_db: str = ''):
    """
    Creates a fasta file of all ASVs currently annotated with a specific
    (version of a) reference database, e.g. 'UNITE:8.0'. The file is saved to
    bind-mounted directory 'fasta-exports' and can then be used as input to
    the Ampliseq pipeline, as part of taxonomic reannotation procedures.
    """

    _, cursor = connect_db()

    filename = 'export-' + dt.now().strftime("%y%m%d-%H%M%S")

    # Create the fasta file
    logging.info("Exporting fasta file: %s.fasta", filename)

    sql = f"SELECT DISTINCT(a.asv_id), a.asv_sequence \
           FROM public.taxon_annotation ta, public.asv a \
           WHERE a.pid = ta.asv_pid \
           AND reference_db = '{ref_db}';"

    with open(f'/worker/fasta-exports/{filename}.fasta', 'w') as fasta:
        cursor.execute(sql)
        for asv_id, sequence in cursor.fetchall():
            fasta.write('>%s\n%s\n' % (asv_id, sequence))


if __name__ == '__main__':

    import argparse

    PARSER = argparse.ArgumentParser(description=__doc__)

    PARSER.add_argument('--db-dir', default="/blastdbs",
                        help="Directory to store database files in.")
    PARSER.add_argument('--filename', default="asvdb",
                        help="Filename prefix for database files.")
    PARSER.add_argument('--ref', default="",
                        help="Reference database for filtering of ASVs in"
                             "fasta export. Use to return all ASVs currently "
                             "annotated with a specific db.")
    PARSER.add_argument('-v', '--verbose', action="count", default=0,
                        help="Increase logging verbosity (default: warning).")
    PARSER.add_argument('-q', '--quiet', action="count", default=3,
                        help="Decrease logging verbosity (default: warning).")

    ARGS = PARSER.parse_args()

    # Set log level based on the -v and -q args
    # E.g: -v means log level = 10(3-1) = 20 = INFO
    # E.g: -vv means log level = 10(3-2) = 10 = DEBUG
    # E.g: -qqvv means log level = 10(5-2) = 30 = WARNING
    logging.basicConfig(level=(10*(ARGS.quiet - ARGS.verbose)))
    # If a reference database is given, just export a fasta file
    if ARGS.ref:
        create_output_fasta(ARGS.ref)
    # Build a new blast database
    else:
        create_blast_db(ARGS.filename, ARGS.db_dir)
