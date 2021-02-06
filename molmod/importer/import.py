#!/usr/bin/env python3
"""
The mol-mod data importer takes an excel file stream, then rearranges and
inserts the data into the database.
"""

import os
import sys
import json
import select
import logging

from io import BytesIO
from typing import Any

import pandas
import psycopg2
from psycopg2.extras import DictCursor

from db_mapper import DBMapper

DEFAULT_MAPPING = os.path.join(os.path.dirname(__file__), 'data-mapping.json')

class MolModImporter():
    """
    The mol-mod importer class is used to load data into memory, run validation
    and insert it into the database.
    """

    def __init__(self, indata: Any, mapping_file: str=DEFAULT_MAPPING):
        """
        Initializes an importer with an input stream or filename. The `indata`
        variable should be any acceptable input to `pandas.read-excel`, as
        documented at:
        https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.read_excel.html.
        """
        # Before we read anything into memory, we check that we have a working
        # database connection.
        self._connect_db()

        # Read data mapping file to make sure that it's also available
        self.set_mapping(mapping_file)

        # pandas require a seekable stream to read excel, and most piped streams
        # are not seekable. To circumvent this, we check the stream, and read it
        # into a separate stream if needed.
        if not indata.seekable():
            logging.debug("input stream is not seekable, reading into BytesIO.")
            # Note that this reads the entire file into memory.
            indata = BytesIO(indata.buffer.raw.read())
        else:
            logging.debug("stream is seekable")

        self.data = {}
        # read one sheet at the time, so that we can catch any missing sheets
        for sheet in self.data_mapping.sheets:
            try:
                self.data[sheet] = pandas.read_excel(indata, sheet_name=sheet)
            except KeyError:
                logging.warning("Input sheet '%s' not found. Skipping.", sheet)
        logging.info("Excel file read")

    def _connect_db(self):
        """
        Uses environment variables to set postgres connection settings, and
        creates a database connection. A simple query to list datasets is then
        used to verify the connection.

        Pandas has a function for automatically inserting into databases, but it
        relies on sqlalchemy, so we use sqlalchemy here even though it's not
        used in the main app.
        """
        try:
            self.conn = psycopg2.connect(
                user=os.getenv('POSTGRES_USER', 'psql'),
                password=os.getenv('POSTGRES_PASSWORD', ''),
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

    def insert_data(self, dry_run=False):
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

            # execute query
            query = self.data_mapping.as_query(table, data)
            self.cursor.execute(query)

            # retrieve results (if returning) and update data
            retvals = self.cursor.fetchall()
            if retvals:
                for col in retvals[0].keys():
                    data[col] = [r[col] for r in retvals]

        if dry_run:
            logging.info("Dry run, rolling back changes")
            self.conn.rollback()
        else:
            logging.info("Committing changes")
            self.conn.commit()

    def prepare_data(self):
        """
        Reorders the loaded data according to the currently loaded data mapping.
        """
        self.data = self.data_mapping.reorder_data(self.data)

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

    PARSER.add_argument('--dry_run', action='store_true',
                        help=("Performs all transactions, but then issues a "
                              "rollback to the database so that it remains "
                              "unaffected. Note that this will still increment "
                              "id sequences."))
    PARSER.add_argument('-v', '--verbose', action="count", default=0,
                        help="Increase logging verbosity (default: warning).")
    PARSER.add_argument('-q', '--quiet', action="count", default=3,
                        help="Decrease logging verbosity (default: warning).")

    ARGS = PARSER.parse_args()

    logging.basicConfig(level=(10*(ARGS.quiet - ARGS.verbose)))

    # check if there is streaming data available from stdin.
    if not select.select([sys.stdin],[],[],0.0)[0]:
        logging.error("An excel input stream is required")
        PARSER.print_help()
        sys.exit(1)

    IMPORTER = MolModImporter(sys.stdin)
    IMPORTER.prepare_data()
    IMPORTER.insert_data(ARGS.dry_run)
