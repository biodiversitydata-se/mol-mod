#!/usr/bin/env python3
"""
The mol-mod data importer takes an Excel or Tar file stream, then rearranges
and inserts the data into the database. The script is executed inside a running
container using the import_excel.py wrapper.
"""

import hashlib
import json
import logging
import os
import re
import select
import sys
import tarfile
import tempfile
from collections import OrderedDict
from datetime import date
from io import BytesIO
from math import isnan
from pprint import pformat
from typing import List, Mapping, Optional

import numpy
import pandas as pd
import psycopg2
from psycopg2.extras import DictCursor

DEFAULT_MAPPING = os.path.join(os.path.dirname(__file__), 'data-mapping.json')

# Define pandas dict of sheets type. This is what's returned from read_excel()
PandasDict = Mapping[str, pd.DataFrame]


def as_snake_case(text: str) -> str:
    """
    Converts CamelCase to snake_case.

    As a special case, this function converts 'ID' to '_id' instead of '_i_d'.
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
    Creates an SQL insert query base using the given 'table_mapping'.

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
    Formats 'value' in a manner suitable for postgres insert queries.
    """
    if isinstance(value, (str, date)):
        return f"{value}"
    # Missing values, but note that missing ranks are read into pandas and db
    # as empty strings, as it was useful for outputting taxon strings later
    if isnan(value):
        return None
    # psycopg2 don't understand numpy values, so we convert them to regular
    # values
    if isinstance(value, numpy.int64):
        return int(value)

    if isinstance(value, numpy.bool_):
        return bool(value)

    return value


def format_values(data: pd.DataFrame, mapping: dict,
                  start: int = 0, end: Optional[int] = 0) -> str:
    """
    Formats the values in 'data' according to the given 'mapping' in a way that
    is suitable for database insert queries. Only values from 'start' to 'end'
    will be used.
    """
    values = []
    for i in range(start, end):
        row = []
        for field in mapping:
            row += [format_value(data[field][i])]

        values += [tuple(row)]

    return values


def insert_common(data: pd.DataFrame, mapping: dict, db_cursor: DictCursor,
                  batch_size: int = 1000):
    """
    Inserts 'data' into the database based on the given 'mapping'.
    """
    base_query, field_mapping = get_base_query(mapping)

    total = len(data.values)
    start = 0
    end = min(total, batch_size)

    query = base_query + " VALUES %s"

    while start < total:
        logging.info("   * inserting %s to %s", start, end)
        values = format_values(data, field_mapping, start, end)

        try:
            logging.debug("query: %s", query)
            psycopg2.extras.execute_values (
                db_cursor, query, values
            )
        except psycopg2.Error as err:
            logging.error(err)
            logging.error("No data were imported.")
            sys.exit(1)

        start = end
        end = min(total, end + batch_size)


def insert_dataset(data: pd.DataFrame, mapping: dict,
                   db_cursor: DictCursor) -> int:
    """
    Inserts a single dataset into the database, and returns the database 'pid'.
    """
    base_query, field_mapping = get_base_query(mapping['dataset'])

    if len(data.values) != 1:
        logging.error("There must be exactly one dataset to insert")
        sys.exit(1)

    values = format_values(data, field_mapping, 0, 1)

    query = base_query + " VALUES %s RETURNING pid;"

    dataset_id = None
    try:
        logging.debug("query: %s", query)
        ids = psycopg2.extras.execute_values(
            db_cursor, query, values, fetch=True
        )
        dataset_id = ids[0][0]
    except psycopg2.Error as err:
        logging.error(err)
        logging.error("No data were imported.")
        sys.exit(1)

    return dataset_id


def insert_events(data: pd.DataFrame, mapping: dict, db_cursor: DictCursor,
                  batch_size: int = 1000) -> pd.DataFrame:
    """
    Inserts sampling events, reeturning the given dataframe with updated
    'pid''s from the database.
    """
    base_query, field_mapping = get_base_query(mapping['event'])

    total = len(data.values)
    start = 0
    end = min(total, batch_size)

    pids = []
    query = base_query + " VALUES %s RETURNING pid;"
    while start < total:
        logging.info("   * inserting %s to %s", start, end)
        values = format_values(data, field_mapping, start, end)

        try:
            logging.debug("query: %s", query)
            pids += psycopg2.extras.execute_values (
                db_cursor, query, values, fetch=True
            )
        except psycopg2.Error as err:
            logging.error(err)
            logging.error("No data were imported.")
            sys.exit(1)

        start = end
        end = min(total, end + batch_size)

    # assign pids to data for future joins
    return data.assign(pid=[v[0] for v in pids])


def insert_asvs(data: pd.DataFrame, mapping: dict, db_cursor: DictCursor,
                batch_size: int = 1000) -> (pd.DataFrame, int):
    """
    Inserts asv's into the database, returning the database 'pid''s. Unlike the
    other categories asv conflicts returns the id of the previously registered
    entry.
    """
    base_query, field_mapping = get_base_query(mapping['asv'])

    total = len(data.values)
    start = 0
    end = min(total, batch_size)

    # get max asv_id before insert (this helps us figure out which asv's were
    # already in the database).
    db_cursor.execute("SELECT MAX(pid) FROM asv;")
    old_max_pid = db_cursor.fetchone()[0]

    query = f"{base_query} VALUES %s" + \
            "ON CONFLICT (asv_sequence) DO UPDATE SET pid = asv.pid " + \
            "RETURNING pid;"

    pids = []
    while start < total:
        logging.info("   * inserting %s to %s", start, end)
        values = format_values(data, field_mapping, start, end)

        # In the unlikely event of hash collision, i.e. that the MD5 algorithm
        # calculates the same hash for two different sequences, insertion of
        # the 2nd sequence will give a duplicate key value violation error
        # Check by modifying the sequence of an existing seq and run in pgAdmin
        # INSERT INTO asv ("asv_id", "asv_sequence")
        # VALUES ('ASV:919a2aa9d306e4cf3fa9ca02a2aa5730',
        # 'TCGAGAATTTTTCACAATGGGGGAAACCCTGATGGAGCGACGCCG...')
        # ON CONFLICT (asv_sequence) DO UPDATE SET pid = asv.pid RETURNING pid;

        try:
            logging.debug("query: %s", query)
            pids += psycopg2.extras.execute_values (
                db_cursor, query, values, fetch=True
            )
        except psycopg2.Error as err:
            logging.error(err)
            logging.error("No data were imported.")
            sys.exit(1)

        start = end
        end = min(total, end + batch_size)

    # assign pids to data for future joins
    return data.assign(pid=[v[0] for v in pids]), old_max_pid or 0


def compare_annotations(data: pd.DataFrame, db_cursor: DictCursor,
                        batch_size: int = 1000):
    """
    Compares target gene and prediction of incoming ('new') annotations to
    existing, valid ('db') annotations for supplied ASVs (should only include
    ASVs that already exist in db), with the following outcomes and responses:

    --	target	pred	pred	pred	pred

    db	geneA	TRUE	FALSE	TRUE	FALSE
    new	geneA	TRUE	TRUE	FALSE	FALSE
    --	----	Ignore	Check	Check	Ignore

    db	geneA	TRUE	FALSE	TRUE	FALSE
    new	geneB	TRUE	TRUE	FALSE	FALSE
    --	----	Check	Update	ignore	Ignore

    E.g., for top left case: an ASV in a new dataset comes in with an
    annotation for geneA, is also predicted to be a TRUE geneA sequence, and
    this corresponds with what is already noted in the database for that ASV,
    so we do nothing.

    Cancels import if any issues need to be checked and resolved,
    and returns pids for annotations that can be updated directly.

    NOTE: This 'validation' is applied during insertion (rather than before) so
    that we can run it on pre-existing ASVs only. We only compare targets, i.e.
    not taxon annotations as such.
    """

    pid_str = ",".join([str(int) for int in data['asv_pid']])
    # Get target prediction info for matching asvs in db
    query = f"""SELECT asv_id, asv_pid, annotation_target, target_prediction,
               target_criteria
               FROM taxon_annotation ta, asv
               WHERE ta.asv_pid = asv.pid AND asv_pid in ({pid_str})
               AND status = 'valid'
            """
    total = len(data.values)
    start = 0
    end = min(total, batch_size)
    db_annotations = []

    while start < total:

        try:
            db_cursor.execute(query)
            db_annotations += [dict(r) for r in db_cursor.fetchall()]
        except psycopg2.Error as err:
            logging.error(err)
            logging.error("No data were imported.")
            sys.exit(1)

        start = end
        end = min(total, end + batch_size)

        issues = []
        updates = []

        # For every matching annotation record in db
        for d in db_annotations:

            # Get corresponding new record
            nfull = data[data['asv_pid'] == d['asv_pid']].to_dict('records')[0]
            # Only keep common fields, so that we can identify data diffs below
            asv_id = d['asv_id']
            alias = nfull['asv_id_alias']
            del d['asv_id']
            n = dict((k, nfull[k]) for k in d.keys())

            # If annotations differ between incoming data and db
            if (n != d):
                issue = {'asv_id': asv_id, 'new': n, 'db': d,
                         'alias': alias}
                # If same target but different predictions
                # e.g. if ampliseq setup was unintentionally changed
                if (((d['annotation_target'] == n['annotation_target']) &
                     (d['target_prediction'] != n['target_prediction'])) or
                    # ...or if different targets, but same predictions
                    # i.e. different target prediction methods disagree
                    ((d['annotation_target'] != n['annotation_target']) &
                     (d['target_prediction'] is True) &
                     (n['target_prediction'] is True))):
                    # Save for check
                    issues.append(issue)
                # If new True target comes in for ASV with False target
                elif ((d['annotation_target'] != n['annotation_target']) &
                      (d['target_prediction'] is False) &
                      (n['target_prediction'] is True)):
                    # Save for update
                    updates.append(d['asv_pid'])
        # Quit if any issues need resolution
        if len(issues):
            logging.error('Annotation issues that need to be resolved:\n %s',
                          pformat(issues))
            logging.error("No data were imported.")
            sys.exit(1)

        # Return asv_pid:s for any updates to be made
        return updates


def invalidate_annotations(pids: list, db_cursor: DictCursor):
    """
    Takes a list of asv_pid:s, and removes 'valid' status from current
    taxon annotations of these in db.
    """

    pid_str = ",".join([str(int) for int in pids])
    query = f"""UPDATE taxon_annotation
                SET status = 'old'
                WHERE asv_pid IN ({pid_str})
            """
    try:
        db_cursor.execute(query)
    except psycopg2.Error as err:
        logging.error(err)
        logging.error("No data were imported.")
        sys.exit(1)


def read_data_file(data_file: str, sheets: List[str]):
    """
    Opens and reads the given 'sheets' from 'data_file'. 'data_file' must be a
    valid excel or tar file.
    """

    # Check input file format
    is_tar = tarfile.is_tarfile(data_file)
    if is_tar:
        tar = tarfile.open(data_file)
    else:
        try:
            pd.read_excel(data_file)
        except (ValueError, KeyError):
            logging.error("Input neither recognized as tar nor as Excel.")
            logging.error('Was your *.tar.gz file not recognized as a tarfile?'
                          ' This sometimes happens when small test archives '
                          'get negative compression ratios. Try adding dummy '
                          'rows to your annotation file and rerun import.')
            sys.exit(1)

    data = {}
    # Read one sheet at the time, to catch any missing sheets
    for sheet in sheets:
        try:
            if is_tar:
                # Find correct file in tar archive
                content = None
                for member in tar:
                    # Ignore parent dir, if any
                    member_name = os.path.basename(member.name)
                    if member_name.split('.')[0] == sheet:
                        csv_file = tar.extractfile(member)
                        content = BytesIO(csv_file.read())
                        csv_file.close()
                if not content:
                    raise KeyError
                try:
                    data[sheet] = pd.read_csv(content)
                except Exception:
                    logging.error("Input file '%s' could not be read. "
                                  "Please inspect file.", member.name)
                    sys.exit(1)
            else:
                data[sheet] = pd.read_excel(data_file, sheet_name=sheet)
        except KeyError:
            logging.error("Input sheet '%s' not found. Aborting.", sheet)
            sys.exit(1)
    logging.info("%s file read", "Tar" if is_tar else "Excel")

    for sheet in data:
        # Drop empty rows and columns, if any
        data[sheet] = data[sheet].dropna(how='all')
        data[sheet] = data[sheet].drop(data[sheet].filter(regex="Unnamed"),
                                       axis='columns')
    # Drop 'domain' column if e.g. ampliseq has included that
    for sheet in ['asv', 'annotation']:
        data[sheet] = data[sheet].drop(columns=['domain'], errors='ignore')
    return data


def handle_dates(dates: pd.Series):
    """
    Removes time digits (e.g. 00:00:00) from (Excel) date / timestamp field,
    as they mess up validation. Does nothing if field is text / string.
    """
    try:
        dates = dates.dt.date
    # E.g. if field is text
    except AttributeError:
        pass
    return dates


def run_import(data_file: str, mapping_file: str, batch_size: int = 1000,
               validate: bool = True, dry_run: bool = False):
    """
    Inserts the data from data_file into the database using the mapping_file.
    """

    logging.info("Connecting to database")
    connection, cursor = connect_db()

    logging.info("Loading mapping file")
    try:
        mapping = json.load(open(mapping_file))
    except json.decoder.JSONDecodeError as err:
        filename = os.path.basename(mapping_file)
        logging.error(f'There is an error in {filename}: {err}')
        sys.exit(1)

    logging.info("Loading data file")
    data = read_data_file(data_file, list(mapping.keys()))

    # Check for possible problem with R-generated Excel file
    if data['dataset'].shape[0] == 0:
        logging.error('Input files seem to not have been read properly. '
                      'Please, check dimensions (#rows, #cols) below:')
        for sheet in ['dataset', 'emof', 'mixs', 'asv', 'annotation']:
            logging.error(f'Sheet {sheet} has dimensions {data[sheet].shape}')
        logging.error('Excel files exported from R have caused this problem '
                      'before. Try opening and saving input in Excel, '
                      'or importing data as *.tar.gz instead.')
        sys.exit(1)

    # Check for field differences between data input and mapping
    logging.info("Checking fields")
    if not compare_fields(data, mapping):
        logging.error('No data were imported.')
        sys.exit(1)

    # Deal with Excel timestamps
    # Requires date fields to exist, so do not move ahead of field check!
    data['event']['eventDate'] = handle_dates(data['event']['eventDate'])
    data['annotation']['date_identified'] = \
        handle_dates(data['annotation']['date_identified'])

    if validate:
        logging.info("Validating input data")
        if not run_validation(data, mapping):
            logging.error("No data were imported.")
            sys.exit(1)

    if not compare_id_fields(data):
        logging.error("No data were imported.")
        sys.exit(1)

    logging.info("Updating defaults")
    update_defaults(data, mapping)

    #
    # Insert DATASET
    #

    logging.info("Inserting data")
    logging.info(" * dataset")
    dataset = insert_dataset(data['dataset'], mapping, cursor)

    #
    # Insert EVENTS
    #

    # Get 'event_pid' from dataset and add as new column
    data['event'] = data['event'].assign(dataset_pid=lambda _: dataset)
    logging.info(" * event")
    data['event'] = insert_events(data['event'], mapping, cursor, batch_size)

    #
    # Insert MIXS
    #

    # Join with 'event' to get 'event_pid' as 'pid'
    events = data['event'].set_index('eventID')
    data['mixs'] = data['mixs'].join(events['pid'], on='eventID')

    logging.info(" * mixs")
    insert_common(data['mixs'], mapping['mixs'], cursor, batch_size)

    #
    # Insert EMOF
    #

    # Join with 'event' to get 'event_pid'
    data['emof'] = data['emof'] \
        .join(events['pid'], on='eventID')
    data['emof'].rename(columns={'pid': 'event_pid'}, inplace=True)

    logging.info(" * emof")
    insert_common(data['emof'], mapping['emof'], cursor, batch_size)

    #
    # Insert ASV
    #

    # Generate 'asv_id' as ASV:<md5-checksum of 'DNA_sequence'>
    data['asv']['asv_id'] = [f'ASV:{hashlib.md5(s.encode()).hexdigest()}'
                             for s in data['asv']['DNA_sequence']]

    logging.info(" * asvs")
    data['asv'], old_max_asv = insert_asvs(data['asv'], mapping,
                                           cursor, batch_size)
    # Drop asv_id column again, as it confuses pandas
    del data['asv']['asv_id']

    #
    # Insert TAXON_ANNOTATION
    #

    # Join with asv to add 'asv_pid'
    asvs = data['asv'].set_index('asv_id_alias')
    data['annotation'] = data['annotation'] \
        .join(asvs['pid'], on='asv_id_alias', how='inner')
    data['annotation'].rename(columns={'pid': 'asv_pid'}, inplace=True)

    # Check annotations for existing asvs
    matches = data['annotation'][data['annotation'].asv_pid <= old_max_asv]
    update_pids = compare_annotations(matches, cursor, batch_size)
    if (update_pids):
        invalidate_annotations(update_pids, cursor)

    # Add new and updated annotations
    annotation = data['annotation'][data['annotation'].asv_pid > old_max_asv]
    if (update_pids):
        updates = \
            data['annotation'][data['annotation'].asv_pid.isin(update_pids)]
        annotation = annotation.append(updates)
    annotation.reset_index(inplace=True)
    logging.info(" * annotations")
    insert_common(annotation, mapping['annotation'], cursor, batch_size)

    #
    # Insert OCCURRENCE
    #

    # Join with asvs to add 'asv_pid'
    occurrences = data['occurrence'].join(asvs['pid'], on='asv_id_alias')
    occurrences.rename(columns={'pid': 'asv_pid'}, inplace=True)

    # Join with events to add 'event_pid'
    # But drop event-level associatedSequences field first,
    # as we also allow users to add associations at asv level,
    # which is what we want to store here
    del events['associatedSequences']
    occurrences = occurrences.join(events, on='eventID')
    occurrences.rename(columns={'pid': 'event_pid'}, inplace=True)

    logging.info(" * occurrences")
    insert_common(occurrences, mapping['occurrence'], cursor, batch_size)

    #
    # Commit or Roll back
    #

    if dry_run:
        logging.info("Dry run, rolling back changes")
        connection.rollback()
    else:
        logging.info("Committing changes")
        connection.commit()


def run_validation(data: PandasDict, mapping: dict):
    """
    Uses 'mapping' to run regexp validation of the fields in data.
    """
    valid = True
    for sheet, fields in mapping.items():
        logging.info(" * %s", sheet)
        for field, settings in fields.items():
            previous_mistake = False
            if 'validation' not in settings:
                continue
            try:
                validator = re.compile(settings['validation'])
            except re.error as err:
                logging.error('Seems to be something wrong with a regular '
                              'expression used in validation. Please check '
                              'data-mapping.json.\nPython says: "%s"', err)
                sys.exit(1)
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
    Uses the 'mapping' dict to set default values in 'data'.
    """
    for sheet, fields in mapping.items():
        logging.info(" * %s", sheet)
        for field, settings in fields.items():
            if 'default' in settings:
                default = settings['default']
                # If field (listed in mapping) is missing from input form
                if field not in data[sheet]:
                    # Add default to all rows
                    data[sheet][field] = [default]*len(data[sheet].values)
                else:
                    # Fill only NaN cells
                    data[sheet][field].fillna(value=default, inplace=True)


def compare_sheets(data: PandasDict, sheet1: str, sheet2: str, field1: str,
                   field2: str = None):
    """
    Compares full sets of values for corresponding fields in different sheets,
    and returns False if these differ.
    """
    if not field2:
        field2 = field1
    set1 = set(data[sheet1][field1])
    set2 = set(data[sheet2][field2])
    diff = set1.difference(set2)
    if diff:
        logging.error('%s value(s) %s in %s sheet not present in %s sheet.',
                      field1, diff, sheet1, sheet2)
        return False
    return True


def compare_id_fields(data: PandasDict):
    """
    Compares sets of key fields between sheets, and returns false if
    if there is any difference.
    """
    nodiff = True
    # Check if any events in dependent sheets are missing from event sheet
    for sheet in ['mixs', 'emof', 'occurrence']:
        nodiff &= compare_sheets(data, sheet, 'event', 'eventID')

    # Check if any events lack occurrences
    nodiff &= compare_sheets(data, 'event', 'occurrence', 'eventID')

    # Check if any asvs lack annotation
    nodiff &= compare_sheets(data, 'asv', 'annotation', 'asv_id_alias')

    return nodiff


def compare_fields(data: PandasDict, mapping: dict):
    """
    Combines booleans returned from compare_sets, and returns False if
    any of these are False (i.e. there is some diff)
    """
    nodiff = True

    # Check if any mapping fields are missing from data input
    for sheet in mapping.keys():
        set1 = set([k for k in mapping[sheet].keys()
                    if k not in [
                        # Fields not expected in input
                        'status', 'targetTable', 'asv_pid',
                        'dataset_pid', 'pid', 'asv_id',
                        'previous_identifications', 'event_pid'
                    ]])
        set2 = set(data[sheet].keys())
        diff = set1.difference(set2)
        if diff:
            logging.error(f'Fields {diff} are missing from sheet {sheet}.')
            nodiff &= False

    # Check if any input fields are missing from mapping
    # Ignore fields that are always expected to be missing, e.g.
    # Unpivoted event fields from asv-table - which are dataset-specific
    events = data['occurrence']['eventID'].tolist()
    # logging.error(f'Events {events}.')
    # Fields used for deriving db fields, or that are moved to derived sheets
    expected = ['eventID', 'DNA_sequence', 'associatedSequences',
                'asv_sequence', 'asv_id_alias', 'order', 'phylum', 'kingdom',
                'class', 'family', 'genus', 'infraspecificEpithet',
                'index', 'otu', 'specificEpithet']
    for sheet in data.keys():
        set1 = set([k for k in data[sheet].keys()
                   if k not in events + expected])
        set2 = set(mapping[sheet].keys())
        diff = set1.difference(set2)
        if diff:
            msg = f"Fields {diff} in sheet '{sheet}' missing from mapping."
            logging.error(msg)
            nodiff &= False

    return nodiff


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

    # Set log level based on ./scripts/import_excel argument
    # E.g: --v means log level = 10(3-2) = 10
    logging.basicConfig(level=(10*(ARGS.quiet - ARGS.verbose)))

    # Check if there is streaming data available from stdin
    # (used in case importer is not executed via import_excel.py)
    if not select.select([sys.stdin], [], [], 0.0)[0]:
        logging.error("An excel input stream is required")
        PARSER.print_help()
        sys.exit(1)

    # Write stdin to a temporary file
    with tempfile.NamedTemporaryFile('rb+') as temp:
        temp.write(sys.stdin.buffer.raw.read())

        run_import(temp.name, ARGS.mapping_file, ARGS.batch_size,
                   # --no_validation -> not True = False
                   not ARGS.no_validation, ARGS.dry_run)
