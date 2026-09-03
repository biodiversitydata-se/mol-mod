#!/usr/bin/env python3
"""
This script is executed inside a running asv-main container, using the
export_data.py wrapper. Depending on arguments added to the wrapper,
the exporter either reads data from event-core-like DwC views and produces
condensed dataset archives, or exports fasta files to be used in taxonomic
reannotation.
"""

from datetime import datetime as dt
import logging
import os
import re
import shutil
import sys
import time
import xml.etree.ElementTree as ET

import psycopg2
from psycopg2.extras import DictCursor
import requests


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
    sql = ("SELECT dataset_id, ipt_resource_id "
           f"FROM dataset WHERE dataset.pid = {pid}")
    cursor.execute(sql)
    result = cursor.fetchone()
    if result is None:
        logging.error(f"No dataset found for pid {pid}")
        return None, None
    else:
        dataset_id, ipt_id = result
        if ipt_id is None:
            logging.error(f"No ipt_resource_id found for pid {pid}")
            return None, None
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


def get_ds_meta(uuid):
    """
    Requests main metadata items for a dataset from the GBIF API. Most of it
    is also in the eml file, but the dataset DOI is not, so that is all we
    still use this for.
    """
    url = f'https://api.gbif.org/v1/dataset/{uuid}'
    response = requests.get(url)
    if response.status_code == 200:
        dataset_info = response.json()
        return dataset_info
    return None


UUID_RE = re.compile(
    r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
VERSION_RE = re.compile(r'\bVersion\s+([0-9]+(?:\.[0-9]+)+)')


def parse_eml_metadata(eml: str) -> dict:
    """
    Extracts the fields the README needs from an IPT EML string: dataset
    title, resource citation, first bibliographic citation, license name and
    the dataset UUID.

    The resource citation is the <citation> element without an identifier=
    attribute; its version is forced to match the packageId, which is the
    authoritative published version (the auto-generated citation string is
    occasionally one step ahead).
    """
    root = ET.fromstring(eml)
    # Drop namespace prefixes so plain tag names work regardless of EML flavour
    for el in root.iter():
        if isinstance(el.tag, str) and '}' in el.tag:
            el.tag = el.tag.split('}', 1)[1]

    def collapse(el):
        if el is None:
            return ''
        return re.sub(r'\s+', ' ', ''.join(el.itertext())).strip()

    dataset = root.find('dataset')

    title = collapse(dataset.find('title')) if dataset is not None else ''

    pkg = root.get('packageId', '')
    m = re.search(r'/v([0-9]+(?:\.[0-9]+)+)$', pkg)
    pkg_version = m.group(1) if m else None
    m = UUID_RE.search(pkg)
    uuid = m.group(0) if m else None
    if not uuid and dataset is not None:
        for alt in dataset.findall('alternateIdentifier'):
            m = UUID_RE.search(alt.text or '')
            if m:
                uuid = m.group(0)
                break

    resource_citation, bibl_citation, bibl_id = '', '', ''
    for cit in root.iter('citation'):
        body = collapse(cit)
        if not body:
            continue
        if cit.get('identifier'):
            if not bibl_citation:
                bibl_citation = body
                bibl_id = (cit.get('identifier') or '').strip()
        elif not resource_citation:
            resource_citation = body

    # Append the bibliographic citation's identifier (DOI or URL) when present
    if bibl_citation and bibl_id:
        link = bibl_id
        if re.match(r'^10\.\d{4,}/\S+$', bibl_id):
            link = f'https://doi.org/{bibl_id}'
        if link not in bibl_citation:
            bibl_citation = f'{bibl_citation} {link}'

    if resource_citation and pkg_version:
        cm = VERSION_RE.search(resource_citation)
        if cm and cm.group(1) != pkg_version:
            old = re.escape(cm.group(1))
            resource_citation = re.sub(
                rf'\bVersion {old}\b', f'Version {pkg_version}',
                resource_citation)
            resource_citation = re.sub(
                rf'([?&]v=){old}\b', rf'\g<1>{pkg_version}', resource_citation)
            logging.warning("EML citation version %s != packageId %s; using %s",
                            cm.group(1), pkg_version, pkg_version)

    license_name = ''
    if dataset is not None:
        licensed = dataset.find('licensed')
        if licensed is not None:
            license_name = (collapse(licensed.find('licenseName'))
                            or collapse(licensed.find('url')))
        if not license_name:
            rights = dataset.find('intellectualRights')
            if rights is not None:
                license_name = (collapse(rights.find('.//citetitle'))
                                or collapse(rights))

    return {
        'title': title or 'N/A',
        'citation': resource_citation,
        'bibl_citation': bibl_citation or 'N/A',
        'license': license_name or 'N/A',
        'uuid': uuid,
    }


def make_readme(ipt_resource_id, dir):
    """
    Creates a README.txt in 'dir' from the dataset's eml.xml (already
    downloaded there by get_eml_file), filling the template's [API data]
    placeholder.

    Title, citation, version and license all come from the EML, so the README
    always matches the exported IPT version. Only the dataset DOI is fetched
    from the GBIF API, since it is not part of the IPT EML; a failure there
    (e.g. GBIF maintenance) leaves DOI as 'N/A' rather than aborting export.
    """
    destination_path = os.path.join(dir, 'README.txt')
    eml_path = os.path.join(dir, 'eml.xml')
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(script_dir, 'readme-template.txt')

    try:
        with open(eml_path, 'r', encoding='utf-8') as eml_file:
            eml = eml_file.read()
        meta = parse_eml_metadata(eml)
    except (OSError, ET.ParseError) as err:
        logging.error("Could not read metadata from %s: %s", eml_path, err)
        return False

    if not meta['citation']:
        logging.error("No resource citation found in %s", eml_path)
        return False

    doi = 'N/A'
    if meta['uuid']:
        data = get_ds_meta(meta['uuid'])
        if data and data.get('doi'):
            doi = data['doi']
        else:
            logging.warning("Could not fetch DOI from GBIF for %s",
                            ipt_resource_id)
    else:
        logging.warning("No UUID in EML for %s; DOI left as N/A",
                        ipt_resource_id)

    with open(template_path, 'r', encoding='utf-8') as readme:
        template = readme.read()

    replacement = (
        f"Dataset name: {meta['title']}\n\n"
        f"Citation: {meta['citation']}\n\n"
        f"Bibliographic citation: {meta['bibl_citation']}\n\n"
        f"License: {meta['license']}\n\n"
        f"DOI: {doi}\n"
    )
    readme = template.replace('[API data]', replacement)
    with open(destination_path, 'w', encoding='utf-8') as file:
        file.write(readme)
    return True


def export_datasets(pids: str):
    """
    Exports data and metadata for a list of / all datasets to compressed files.
    For each dataset, calls functions to get eml file from IPT, key metadata
    from GBIF API, and data from DB.
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
        dataset_id, ipt_id = get_dataset_ids(cursor, pid)
        if dataset_id is None:
            continue
        logging.info("Exporting dataset: %s", dataset_id)

        # Make clean dataset dir
        dir = os.path.join('/app/data-volumes/exports', dataset_id)
        if os.path.exists(dir):
            shutil.rmtree(dir, ignore_errors=True)
        os.makedirs(dir, exist_ok=True)

        # Get eml file from IPT
        if not get_eml_file(ipt_id, dir):
            shutil.rmtree(dir, ignore_errors=True)
            continue

        # Add key metadata from Bioatlas to readme
        if not make_readme(ipt_id, dir):
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

    dir = '/app/data-volumes/fasta-exports'
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
