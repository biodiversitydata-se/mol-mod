#!/usr/bin/env python3
"""
The mol-mod data importer takes an Excel file stream, then rearranges and
inserts the data into the database.
"""

import json
import logging
import os
import select
import sys
import tarfile
import tempfile
from io import BytesIO

import pandas
import psycopg2
from db_mapper import DBMapper
from psycopg2.extras import DictCursor

DEFAULT_MAPPING = os.path.join(os.path.dirname(__file__), 'data-mapping.json')


class MolModImporter():
    """
    The mol-mod importer class is used to load data into memory, run validation
    and insert validated data into the database.
    """

    def __init__(self, data_file: str, mapping_file: str = DEFAULT_MAPPING):
        """
        Initializes an importer with an input stream or filename. The `indata`
        variable should be any acceptable input to `pandas.read-excel`, as
        documented at:
        https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.read_excel.html.
        """
        # Check that we have a working database connection.
        self._connect_db()

        # Read data mapping file to make sure that it's also available
        self.set_mapping(mapping_file)

        self.data = {}

        # Check input file format
        is_tar = tarfile.is_tarfile(data_file)
        if is_tar:
            tar = tarfile.open(data_file)
        else:
            try:
                pandas.read_excel(data_file)
            except ValueError:
                logging.error("Input neither recognized as tar nor as Excel.")
                sys.exit(1)

        # Read one sheet at the time, so that we can catch any missing sheets
        for sheet in self.data_mapping.sheets:
            try:
                if is_tar:
                    # find the correct file in the tar archive
                    content = None
                    for member in tar:
                        if member.name.split('.')[0] == sheet:
                            csv_file = tar.extractfile(member)
                            content = BytesIO(csv_file.read())
                            csv_file.close()
                    if not content:
                        raise KeyError
                    self.data[sheet] = pandas.read_csv(content)
                else:
                    self.data[sheet] = pandas.read_excel(data_file,
                                                         sheet_name=sheet)
            except KeyError:
                logging.warning("Input sheet '%s' not found. Skipping.", sheet)
        logging.info("%s file read", "Tar" if is_tar else "Excel")

    def _connect_db(self, pass_file='/run/secrets/postgres_pass'):
        """
        Uses environment variables to set postgres connection settings, and
        creates a database connection. A simple query to list datasets is then
        used to verify the connection.
        """
        try:
            with open(pass_file) as password:
                password = password.read()
        except FileNotFoundError:
            logging.error("Could not read postgres pwd from %s", pass_file)
            sys.exit(1)

        try:
            self.conn = psycopg2.connect(
                user=os.getenv('POSTGRES_USER', 'psql'),
                password=password,
                database=os.getenv('POSTGRES_DB', 'db'),
                host=os.getenv('POSTGRES_HOST', 'localhost'),
                port=os.getenv('POSTGRES_PORT', '5432')
            )
            logging.info("Connected to PostgreSQL database")
            self.cursor = self.conn.cursor(cursor_factory=DictCursor)

            self.cursor.execute("SELECT * FROM public.dataset;")
            logging.debug("Database connection verified")
        except psycopg2.OperationalError as err:
            logging.error("Could not connect to postgres database")
            logging.error(err)
            sys.exit(1)

    def insert_data(self, dry_run: bool = False, batch_size: int = 0):
        """
        Executes insert queries for the currently loaded data. The data is
        inserted in a single transaction, committing all changes once all
        queries have completed, unless `dry_run` is set, in which case a
        rollback is issued instead.
        """
        logging.info("Inserting data into database")

        # create a session to make sure that the transaction is atomic.
        for table, data in self.data.items():
            logging.info(" - %s", table)

            # check for references, and update fields
            self.data_mapping.update_references(table, self.data)

            total = len(data.values)
            if batch_size <= 0:
                batch_size = total

            update_vals = {}

            # execute query
            inserted = 0
            while total > inserted:
                stop = min(total, inserted + batch_size)
                logging.debug("inserting %s to %s", inserted, stop)
                query = self.data_mapping.as_query(table, data,
                                                   inserted, batch_size)
                self.cursor.execute(query)
                inserted += batch_size

                # update the return values
                if self.data_mapping.is_returning(table):
                    retvals = self.cursor.fetchall()
                    for col in retvals[0].keys():
                        if col not in update_vals:
                            update_vals[col] = []
                        update_vals[col] += [c[col] for c in retvals]

            for col in update_vals:
                data[col] = update_vals[col]

        if dry_run:
            logging.info("Dry run, rolling back changes")
            self.conn.rollback()
        else:
            logging.info("Committing changes")
            self.conn.commit()

    def prepare_data(self):
        """
        Reorders loaded data according to currently loaded data mapping.
        """
        self.data = self.data_mapping.reorder_data(self.data)

    def run_validation(self):
        """
        Runs the validation regexp for all values to see that they match.
        """
        logging.info("Validating tables")
        valid = True
        for table, data in self.data.items():
            logging.info(" -- %s", table)
            valid &= self.data_mapping.validate(table, data)
        return valid

    def set_mapping(self, filename: str):
        """
        Reads `filename`, as JSON, into `self.data_mapping`, which will be used
        to map data from imported excel files into the postgres database.
        """
        try:
            self.data_mapping = DBMapper(filename)
            return
        except FileNotFoundError:
            logging.error("Could not find data mapping file: %s", filename)
        except json.decoder.JSONDecodeError as err:
            logging.error("Invalid JSON in mapping file: %s", err)
        sys.exit(1)


if __name__ == '__main__':

    import argparse

    PARSER = argparse.ArgumentParser(description=__doc__)

    PARSER.add_argument('--dry-run', action='store_true',
                        help=("Performs all transactions, but then issues a "
                              "rollback to the database so that it remains "
                              "unaffected. This will still increment "
                              "id sequences."))
    PARSER.add_argument('--batch_size', type=int, default=100,
                        help=("Sets the max number of rows to be inserted for "
                              "each insert query."))
    PARSER.add_argument('--no-validation', action="store_true",
                        help="Do NOT validate the data before insertion.")
    PARSER.add_argument('-v', '--verbose', action="count", default=0,
                        help="Increase logging verbosity (default: warning).")
    PARSER.add_argument('-q', '--quiet', action="count", default=3,
                        help="Decrease logging verbosity (default: warning).")

    ARGS = PARSER.parse_args()

    logging.basicConfig(level=(10*(ARGS.quiet - ARGS.verbose)))

    # check if there is streaming data available from stdin.
    if not select.select([sys.stdin], [], [], 0.0)[0]:
        logging.error("An excel input stream is required")
        PARSER.print_help()
        sys.exit(1)

    # write stdin to a temporary file
    with tempfile.NamedTemporaryFile('rb+') as temp:
        temp.write(sys.stdin.buffer.raw.read())

        IMPORTER = MolModImporter(temp.name)
        IMPORTER.prepare_data()
        if not ARGS.no_validation:
            if not IMPORTER.run_validation():
                logging.error("Data did not pass validation")
                sys.exit(1)
            logging.info("Data passed validation")
        IMPORTER.insert_data(ARGS.dry_run, ARGS.batch_size)
