#!/usr/bin/env python3
"""
The mol-mod data importer takes an Excel or Tar file stream, then rearranges
and inserts the data into the database.
"""

import json
import logging
import os
import re
import select
import sys
import tarfile
import tempfile
from collections import OrderedDict
from io import BytesIO
from typing import List, Mapping, Optional

import numpy
import pandas
import psycopg2
from pandas import Timestamp
from psycopg2.extras import DictCursor

DEFAULT_MAPPING = os.path.join(os.path.dirname(__file__), 'data-mapping.json')

# Define pandas dict of sheets type. This is what's returned from read_excel()
PandasDict = Mapping[str, pandas.DataFrame]


def as_snake_case(text: str) -> str:
    """
    Converts CamelCase to snake_case.

    As a special case, this function converts `ID` to `_id` instead of `_i_d`.
    """
    output = ""
    for i, char in enumerate(text):
        if char.isupper() and i != 0:
            # preserve _id
            if not (char == 'D' and text[i-1] == 'I'):
                output += "_"
        output += char.lower()
    return output


def connect_db(pass_file='/run/secrets/postgres_pass'):
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


def get_base_query(table_mapping: dict):
    """
    Creates an SQL insert query base using the given `table_mapping`.

    Note that the retured query will not be complete as it will not include any
    data values.
    """

    field_map = OrderedDict()
    for field, settings in table_mapping.items():
        if field in ['targetTable']:
            continue

        field_map[field] = f'"{settings.get("field", as_snake_case(field))}"'

    fields = ", ".join(list(field_map.values()))

    return f"INSERT INTO {table_mapping['targetTable']} ({fields})", field_map


def format_value(value):
    """
    Formats `value` in a manner suitable for postgres insert queries.
    """
    if isinstance(value, (str, Timestamp)):
        return f"'{value}'"
    if value is None:
        return 'NULL'
    if numpy.isnan(value):
        return "'NaN'"
    return value


def format_values(data: pandas.DataFrame, mapping: dict,
                  start: int = 0, end: Optional[int] = 0) -> str:
    """
    Formats the values in `data` according to the given `mapping` in a way that
    is suitable for database insert queries. Only values from `start` to `end`
    will be used.
    """
    values = []
    for i in range(start, end):
        value = []
        for field in mapping:
            value += [format_value(data[field][i])]

        values += [f'({", ".join(map(str, value))})']

    return values


def insert_common(data: pandas.DataFrame, mapping: dict, db_cursor: DictCursor,
                  batch_size: int = 1000):
    """
    Inserts `data` into the database based on the given `mapping`.
    """
    base_query, field_mapping = get_base_query(mapping)

    total = len(data.values)
    start = 0
    end = min(total, batch_size)

    while start < total:
        logging.info("   * inserting %s to %s", start, end)
        values = format_values(data, field_mapping, start, end)

        query = f"{base_query} VALUES {', '.join(values)};"

        try:
            db_cursor.execute(query)
        except psycopg2.Error as err:
            logging.error(err)
            sys.exit(1)

        start = end
        end = min(total, end + batch_size)


def insert_dataset(data: pandas.DataFrame, mapping: dict,
                   db_cursor: DictCursor) -> int:
    """
    Inserts a single dataset into the database, and returns the database `pid`.
    """
    base_query, field_mapping = get_base_query(mapping['dataset'])

    if len(data.values) != 1:
        logging.error("There must be exactly one dataset to insert")
        sys.exit(1)

    values = format_values(data, field_mapping, 0, 1)
    query = f"{base_query} VALUES {', '.join(values)} RETURNING pid;"

    try:
        db_cursor.execute(query)
    except psycopg2.Error as err:
        logging.error(err)
        sys.exit(1)

    return db_cursor.fetchall()[0]['pid']


def insert_events(data: pandas.DataFrame, mapping: dict, db_cursor: DictCursor,
                  batch_size: int = 1000) -> pandas.DataFrame:
    """
    Inserts sampling events, reeturning the given dataframe with updated
    `pid`'s from the database.
    """
    base_query, field_mapping = get_base_query(mapping['event'])

    total = len(data.values)
    start = 0
    end = min(total, batch_size)

    pids = []
    while start < total:
        logging.info("   * inserting %s to %s", start, end)
        values = format_values(data, field_mapping, start, end)

        query = f"{base_query} VALUES {', '.join(values)} RETURNING pid;"

        try:
            db_cursor.execute(query)
            pids += [r['pid'] for r in db_cursor.fetchall()]
        except psycopg2.Error as err:
            logging.error(err)
            sys.exit(1)

        start = end
        end = min(total, end + batch_size)

    # assign pids to data for future joins
    return data.assign(pid=pids)


def insert_asvs(data: pandas.DataFrame, mapping: dict, db_cursor: DictCursor,
                batch_size: int = 1000) -> pandas.DataFrame:
    """
    Inserts asv's into the database, returning the database `pid`'s. Unlike the
    other categories asv conflicts returns the id of the previously registered
    entry.
    """
    base_query, field_mapping = get_base_query(mapping['asv-table'])

    total = len(data.values)
    start = 0
    end = min(total, batch_size)

    pids = []
    while start < total:
        logging.info("   * inserting %s to %s", start, end)
        values = format_values(data, field_mapping, start, end)

        query = f"{base_query} VALUES {', '.join(values)} " + \
                "ON CONFLICT (asv_sequence) DO UPDATE SET pid = asv.pid " + \
                "RETURNING pid;"

        try:
            db_cursor.execute(query)
            pids += [r['pid'] for r in db_cursor.fetchall()]
        except psycopg2.Error as err:
            logging.error(err)
            sys.exit(1)

        start = end
        end = min(total, end + batch_size)

    # assign pids to data for future joins
    return data.assign(pid=pids)


def read_data_file(data_file: str, sheets: List[str]):
    """
    Opens and reads the given `sheets` from `data_file`. `data_file` must be a
    valid excel or tar file.
    """

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

    data = {}
    # Read one sheet at the time, to catch any missing sheets
    for sheet in sheets:
        # occurrences are taken from the asv-table sheet, so we skip reading it
        if sheet == 'occurrence':
            continue
        try:
            if is_tar:
                # Find correct file in tar archive
                content = None
                for member in tar:
                    if member.name.split('.')[0] == sheet:
                        csv_file = tar.extractfile(member)
                        content = BytesIO(csv_file.read())
                        csv_file.close()
                if not content:
                    raise KeyError
                data[sheet] = pandas.read_csv(content)
            else:
                data[sheet] = pandas.read_excel(data_file, sheet_name=sheet)
        except KeyError:
            logging.error("Input sheet '%s' not found. Aborting.", sheet)
            sys.exit(1)
    logging.info("%s file read", "Tar" if is_tar else "Excel")

    for sheet in data:
        # Drop empty rows and columns, if any
        data[sheet] = data[sheet].dropna(how='all')
        data[sheet] = data[sheet].drop(data[sheet].filter(regex="Unnamed"),
                                       axis='columns')

    return data


def run_import(data_file: str, mapping_file: str, batch_size: int = 1000,
               validate: bool = True, dry_run: bool = False):
    """
    Inserts the data from data_file into the database using the mapping_file.
    """

    logging.info("Connecting to database")
    connection, cursor = connect_db()

    logging.info("Loading mapping file")
    mapping = json.load(open(mapping_file))

    logging.info("Loading data file")
    data = read_data_file(data_file, list(mapping.keys()))

    if validate:
        logging.info("Validating input data")
        if not run_validation(data, mapping):
            sys.exit(1)

    logging.info("Updating defaults")
    update_defaults(data, mapping)

    logging.info("Inserting data")
    logging.info(" * dataset")
    dataset = insert_dataset(data['dataset'], mapping, cursor)

    # update 'event' with dataset_ids
    data['event'] = data['event'].assign(dataset_pid=lambda _: dataset)

    logging.info(" * event")
    data['event'] = insert_events(data['event'], mapping, cursor, batch_size)

    # join 'event' with 'mixs' to get pid's for mixs
    events = data['event'].set_index('event_id_alias')
    data['mixs'] = data['mixs'] \
        .join(events, lsuffix="_joined", on='event_id_alias')

    logging.info(" * mixs")
    insert_common(data['mixs'], mapping['mixs'], cursor, batch_size)

    # join 'event' with 'emof' to get references for emof
    data['emof'] = data['emof'] \
        .join(events, lsuffix="_joined", on='event_id_alias')
    data['emof'].rename(columns={'pid': 'event_pid'}, inplace=True)

    logging.info(" * emof")
    insert_common(data['emof'], mapping['emof'], cursor, batch_size)

    logging.info(" * asvs")
    data['asv-table'] = insert_asvs(data['asv-table'], mapping, cursor,
                                    batch_size)

    # join asv's and annotations to add asv pid's
    asvs = data['asv-table'].set_index('asv_id_alias')
    data['annotation'] = data['annotation'] \
        .join(asvs, lsuffix="_joined", on='asv_id_alias')
    data['annotation'].rename(columns={'pid': 'asv_pid'}, inplace=True)

    logging.info(" * annotations")
    insert_common(data['annotation'],
                  mapping['annotation'], cursor, batch_size)

    # create occurrence table from asv-table
    id_columns = ['pid', 'asv_id_alias', 'DNA_sequence', 'associatedSequences',
                  'kingdom', 'phylum', 'class', 'order', 'family', 'genus',
                  'specificEpithet', 'infraspecificEpithet', 'otu']
    occurrences = data['asv-table'] \
        .melt(id_columns,
              var_name='event_id_alias',
              value_name='organism_quantity')

    # join with events, and rename asv pid to set foreign keys
    occurrences.rename(columns={'pid': 'asv_pid'}, inplace=True)
    occurrences = occurrences \
        .join(events, lsuffix="_joined", on='event_id_alias')
    occurrences.rename(columns={'pid': 'event_pid'}, inplace=True)

    # first set all missing fields to empty strings instead of NaN
    occurrences = occurrences.fillna("")

    # remove 0 occurrence rows, and reset the index so that the removed rows
    # will not be referenced.
    occurrences = occurrences[occurrences.organism_quantity > 0]
    occurrences.reset_index(inplace=True)

    # then concat all the fields
    tax_fields = ["kingdom", "phylum", "class", "order", "family", "genus",
                  "specificEpithet", "infraspecificEpithet", "otu"]
    occurrences['previous_identifications'] = \
        ["|".join(z) for z in zip(*[occurrences[f] for f in tax_fields])]

    logging.info(" * occurrences")
    insert_common(occurrences, mapping['occurrence'], cursor, batch_size)

    if dry_run:
        logging.info("Dry run, rolling back changes")
        connection.rollback()
    else:
        logging.info("Committing changes")
        connection.commit()


def run_validation(data: PandasDict, mapping: dict):
    """
    Uses `mapping` to run regexp validation of the fields in data.
    """
    valid = True
    for sheet, fields in mapping.items():
        logging.info(" * %s", sheet)
        for field, settings in fields.items():
            previous_mistake = False
            if 'validation' not in settings:
                continue
            validator = re.compile(settings['validation'])
            for value in data[sheet][field]:
                if not validator.fullmatch(str(value)):
                    valid = False
                    if not previous_mistake:
                        logging.warning(" - malformed value for %s", field)
                        logging.warning(' - validator: "%s"',
                                        settings['validation'])
                        previous_mistake = True
                    logging.warning("offending value: %s", value)
    if valid:
        logging.info("Validation successful")
    else:
        logging.error("Validation failed")

    return valid


def update_defaults(data: PandasDict, mapping: dict):
    """
    Uses the `mapping` dict to set default values in `data`.
    """
    for sheet, fields in mapping.items():
        logging.info(" * %s", sheet)
        for field, settings in fields.items():
            if 'default' in settings:
                default = settings['default']
                if field not in data[sheet]:
                    data[sheet][field] = [default]*len(data[sheet].values)
                else:
                    data[sheet][field].fillna(default)


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
    PARSER.add_argument('--mapping_file', default=DEFAULT_MAPPING,
                        help=("Sets the data mapping file to use for field "
                              "mapping and validation."))
    PARSER.add_argument('--no-validation', action="store_true",
                        help="Do NOT validate the data before insertion.")
    PARSER.add_argument('-v', '--verbose', action="count", default=0,
                        help="Increase logging verbosity (default: warning).")
    PARSER.add_argument('-q', '--quiet', action="count", default=3,
                        help="Decrease logging verbosity (default: warning).")

    ARGS = PARSER.parse_args()

    logging.basicConfig(level=(10*(ARGS.quiet - ARGS.verbose)))

    # Check if there is streaming data available from stdin.
    if not select.select([sys.stdin], [], [], 0.0)[0]:
        logging.error("An excel input stream is required")
        PARSER.print_help()
        sys.exit(1)

    # Write stdin to a temporary file
    with tempfile.NamedTemporaryFile('rb+') as temp:
        temp.write(sys.stdin.buffer.raw.read())

        run_import(temp.name, ARGS.mapping_file, ARGS.batch_size,
                   not ARGS.no_validation, ARGS.dry_run)
