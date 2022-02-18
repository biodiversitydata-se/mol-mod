#!/usr/bin/env python3
"""
This tool can be used to generate and remove artificial datasets for use during
development.
"""

import logging
import random
import subprocess
import sys
import uuid
from datetime import datetime

# load database connection variables from the environment file
ENV = {}
for line in open('../.env'):
    line = line.strip()
    if not line or line[0] == '#':
        continue
    option, value = line.split('=')
    ENV[option] = value.strip("'")


def random_string(length, letters="abcdefghijklmnopqrstuvwxyz"):
    """
    Returns a random string  of length `length` from a set of letters.
    """
    return "".join([random.choice(letters) for _ in range(length)])


def execute_on_db(query):
    """
    Executes a query in the database and returns the output.

    Note that this function uses command line queries instead of using the API.
    This is to be completely independent from the rest of the implementation.
    """
    user = ENV.get('POSTGRES_USER', 'postgres')
    database = ENV.get('POSTGRES_DB', 'asv')

    cmd = ['docker', 'exec', 'asv-db', 'psql', '-U', user, database, '-c',
           query]

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    output, error = process.communicate()

    if error:
        logging.error('error: %s', error)
        sys.exit(1)

    # format the output as a list of dictionaries to be a bit easier to work
    # with.
    output = output.decode('utf-8')
    output = output.split('\n')
    headers = [h.strip() for h in output[0].split('|')]
    retvals = []
    for row in output[2:]:
        if row.startswith('('):
            # this is to check if we've gotten to the row-count-line at the end
            # of queries, ex:
            #
            #   dataset_id ...
            #   ---------- ...
            #   dataset_1  ...
            #   ...
            #   dataset_14
            #   (14 rows)
            #
            break
        values = [v.strip() for v in row.split('|')]
        retvals += [dict(zip(headers, values))]

    return retvals


def print_datasets():
    """
    This function prints a human readable list of which datasets are currently
    available in the database.
    """
    query = 'SELECT dataset_id AS id FROM dataset;'
    datasets = execute_on_db(query)
    real = [d for d in datasets if not d['id'].startswith('TEST')]
    test = [d for d in datasets if d['id'].startswith('TEST')]
    if not datasets:
        logging.info("There are no datasets in the database")
    if real:
        logging.info("Real datasets:")
        for dataset in real:
            logging.info("  - %s", dataset['id'])
    if test:
        logging.info("Test datasets:")
        for dataset in test:
            logging.info("  - %s", dataset['id'])


def insert_random_sampling_event(dataset):
    """
    Inserts a sampling event into the given dataset, with all required fields
    containing random data.
    """
    event_id = f"{dataset}-{uuid.uuid1().hex}"
    event_date = datetime.today().strftime('%Y-%m-%d')
    sampling_protocol = 'test'
    location_id = 'test'
    decimal_latitude = random.random() * 180 - 90
    decimal_longitude = random.random() * 360 - 180

    execute_on_db(f"""INSERT INTO sampling_event(
                      event_id, dataset_id,
                      event_date, sampling_protocol,
                      location_id,
                      decimal_latitude, decimal_longitude)
                      VALUES('{event_id}', '{dataset}', '{event_date}',
                             '{sampling_protocol}',
                             '{location_id}',
                             '{decimal_latitude}', '{decimal_longitude}');
                   """)
    return event_id


def insert_random_mixs(dataset):
    """
    inserts random values into the mixs table.
    One entry for each sampling event
    in the given dataset.
    """
    events = execute_on_db(f"""SELECT event_id FROM sampling_event
                               WHERE dataset_id = '{dataset}';""")

    for event_id in [event['event_id'] for event in events]:
        target_gene = random_string(20)
        target_subfragment = random_string(20)
        pcr_primer_name_forward = random_string(20)
        pcr_primer_forward = random_string(10, 'ACTG')
        pcr_primer_name_reverse = random_string(20)
        pcr_primer_reverse = random_string(10, 'ACTG')
        env_broad_scale = random_string(20)
        env_local_scale = random_string(20)
        env_medium = random_string(20)

        execute_on_db(f"""INSERT INTO mixs(event_id, target_gene,
                                           target_subfragment,
                                           pcr_primer_name_forward,
                                           pcr_primer_forward,
                                           pcr_primer_name_reverse,
                                           pcr_primer_reverse,
                                           env_broad_scale, env_local_scale,
                                           env_medium
                                           )
                            VALUES('{event_id}', '{target_gene}',
                                   '{target_subfragment}',
                                   '{pcr_primer_name_forward}',
                                   '{pcr_primer_forward}',
                                   '{pcr_primer_name_reverse}',
                                   '{pcr_primer_reverse}', '{env_broad_scale}',
                                   '{env_local_scale}', '{env_medium}');
                        """)

# I want all columns as variables in this function, so I want to have a lot
# of local variables.
#
# pylint: disable=too-many-locals


def insert_random_asvs(dataset, number, batch=100):
    """
    Inserts `number` random asv's into the dataset, prefixed with the dataset
    id so that they can be removed when the test dataset is purged.
    """
    current_batch = []
    for _ in range(int(number)):
        asv_id = f'{dataset}-{uuid.uuid1().hex}'[:36]
        length = random.randint(200, 2500)
        sequence = random_string(length, "ACTG")
        current_batch += [f"('{asv_id}', '{sequence}')"]
        if len(current_batch) >= batch:
            execute_on_db(f"""INSERT INTO asv(asv_id, asv_sequence)
                              VALUES {",".join(current_batch)};""")
            current_batch = []
    if current_batch:
        execute_on_db(f"""INSERT INTO asv(asv_id, asv_sequence)
                            VALUES {",".join(current_batch)};""")


def insert_random_taxon_annotations(dataset, batch=100):
    """
    Inserts a random taxon annotation for each asv associated with the given
    dataset.
    """
    asv_query = f"SELECT asv_id FROM asv WHERE asv_id LIKE '{dataset}%';"
    asvs = [a['asv_id'] for a in execute_on_db(asv_query)]

    current_batch = []
    for asv_id in asvs:
        status = 'valid'
        kingdom = random.choice(['Bacteria', 'Fungi', 'Archaea', 'Protozoa',
                                 'Chromista', 'Plantae', 'Animalia'])
        phylum = random_string(20)
        t_class = random_string(20)
        oorder = random_string(10)
        family = random_string(15)
        genus = random_string(25)
        specific_epithet = random_string(20)
        date_identified = (f'{random.randint(1980,2020)}-'
                           f'{random.randint(1,12)}-'
                           f'{random.randint(1,28)}')
        reference_db = random_string(20)
        annotation_algorithm = random_string(20)
        current_batch += [f"""('{asv_id}', '{status}', '{kingdom}', '{phylum}',
                               '{t_class}', '{oorder}', '{family}', '{genus}',
                               '{specific_epithet}', '{date_identified}',
                               '{reference_db}', '{annotation_algorithm}'
                               )"""]

        if len(current_batch) >= batch:
            execute_on_db(f"""INSERT INTO taxon_annotation(asv_id, status,
                                                           kingdom, phylum,
                                                           class, oorder,
                                                           family, genus,
                                                           specific_epithet,
                                                           date_identified,
                                                           reference_db,
                                                           annotation_algorithm
                                                           )
                              VALUES {",".join(current_batch)};""")
            current_batch = []
    if current_batch:
        execute_on_db(f"""INSERT INTO taxon_annotation(asv_id, status,
                                                        kingdom, phylum,
                                                        class, oorder,
                                                        family, genus,
                                                        specific_epithet,
                                                        date_identified,
                                                        reference_db,
                                                        annotation_algorithm
                                                        )
                            VALUES {",".join(current_batch)};""")


def insert_random_occurences(event_id, dataset, occurences, batch=100):
    """
    Inserts `number` random occurrences into the sampling event, prefixed with
    the dataset id so that they can be removed when the test dataset is purged.
    The occurrences will be assigned to a random asv from the dataset.
    """
    asv_query = f"SELECT asv_id FROM asv WHERE asv_id LIKE '{dataset}%';"
    asvs = [a['asv_id'] for a in execute_on_db(asv_query)]

    current_batch = []
    for _ in range(occurences):
        occurence_id = f'{dataset}-{uuid.uuid1().hex}'
        asv_id = random.choice(asvs)
        organism_quantity = random.randint(1, 1000)
        previous_identifications = ''
        asv_id_alias = ''
        current_batch += [f"""('{occurence_id}', '{event_id}', '{asv_id}',
                               '{organism_quantity}',
                               '{previous_identifications}',
                               '{asv_id_alias}')"""]
        if len(current_batch) >= batch:
            query = f"""INSERT INTO occurrence(occurrence_id, event_id, asv_id,
                                               organism_quantity,
                                               previous_identifications,
                                               asv_id_alias)
                        VALUES {",".join(current_batch)};"""
            execute_on_db(query)
            current_batch = []
    if current_batch:
        query = f"""INSERT INTO occurrence(occurrence_id, event_id, asv_id,
                                            organism_quantity,
                                            previous_identifications,
                                            asv_id_alias)
                    VALUES {",".join(current_batch)};"""
        execute_on_db(query)


def insert_dataset(num_datasets, occurrences):
    """
    Inserts a number of datasets, each having a set number of occurrences.
    All affected tables will have random data.
    """

    datasets = execute_on_db('SELECT * FROM dataset;')
    test_sets = [d for d in datasets if d['dataset_id'].startswith('TEST')]
    test_nums = [int(dataset['dataset_id'][5:]) for dataset in test_sets]

    last_dataset = max(test_nums) if test_nums else 0
    for dataset_num in range(last_dataset+1, last_dataset+num_datasets+1):
        dataset = f'TEST_{dataset_num}'
        logging.info("Inserting %s with %s occurrences", dataset, occurrences)
        execute_on_db(f"""INSERT INTO dataset(dataset_id, provider_email)
                          VALUES('{dataset}', 'TEST');
                       """)
        # insert sampling event
        event_id = insert_random_sampling_event(dataset)

        # and mixs
        insert_random_mixs(dataset)

        # insert asv's (half as many asv's as occurrences)
        insert_random_asvs(dataset, occurrences/2)

        # insert taxon_annotations for the asv's
        insert_random_taxon_annotations(dataset)

        # and finally occurrences
        insert_random_occurences(event_id, dataset, occurrences)


def purge_test_datasets():
    """
    Removes all datasets where the dataset_id start with TEST, as well as all
    the associated data for these datasets.
    """
    # remove occurrences
    logging.info("Removing test occurrences")
    execute_on_db("DELETE FROM occurrence WHERE occurrence_id LIKE 'TEST%'")

    # remove taxon annotations
    logging.info("Removing test taxon annotations")
    execute_on_db("DELETE FROM taxon_annotation WHERE asv_id LIKE 'TEST%'")

    # remove asvs
    logging.info("Removing test asvs")
    execute_on_db("DELETE FROM asv WHERE asv_id LIKE 'TEST%'")

    # remove mixs
    logging.info("Removing test mixs")
    execute_on_db("DELETE FROM mixs WHERE event_id LIKE 'TEST%';")

    # remove sampling events
    logging.info("Removing test sampling events")
    execute_on_db("DELETE FROM sampling_event WHERE dataset_id LIKE 'TEST%';")

    logging.info("Removing test datasets")
    execute_on_db("DELETE FROM dataset WHERE dataset_id LIKE 'TEST%';")


if __name__ == '__main__':
    import argparse

    PARSER = argparse.ArgumentParser(description=__doc__)

    PARSER.add_argument("action",
                        help=("The database action to perform. Valid options "
                              "are 'list', 'insert', and 'purge'."))
    PARSER.add_argument("--datasets", "-d", type=int, default=1,
                        help=("sets the number of test datasets to insert "
                              "into the database, when running 'insert'"))
    PARSER.add_argument("--occurrences", "-o", type=int, default=10000,
                        help=("sets the number of occurrences to insert to "
                              "new test datasets"))
    PARSER.add_argument("--host", default='http://localhost:5000',
                        help="sets the host for testing endpoints")
    PARSER.add_argument("--replicates", "-r", type=int, default=100,
                        help=("sets the number of replicate requests when "
                              "timing endpoints"))

    ARGS = PARSER.parse_args()

    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                        datefmt='%H:%M:%S',
                        level=logging.INFO)

    if ARGS.action == 'list':
        print_datasets()
    elif ARGS.action == 'insert':
        insert_dataset(ARGS.datasets, ARGS.occurrences)
    elif ARGS.action == 'purge':
        purge_test_datasets()
    else:
        logging.error("Unknown action '%s'", ARGS.action)
