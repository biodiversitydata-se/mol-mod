#!/usr/bin/env python3

'''
Creates BLAST DB from Amplicon Sequence Variant (ASV) DB view (PostgreSQL),
exposed via API (PostgREST), and BLASTs TSV query seqs against this DB (as a test).
Saves output to dataframe, and prints table to screen.
'''
import json
import os
import subprocess
from io import StringIO
from subprocess import check_output

import pandas as pd
import requests
from tabulate import tabulate


def main():
    target_fa = 'misc/asv.fa'
    query_fa = 'misc/query1.fa'
    db = 'misc/blastdb/asvdb'

    # Get fasta file from API view
    get_fasta_from_api(target_fa)

    # Make BLAST db from fasta file
    subprocess.call(f"makeblastdb -in {target_fa} -out {db} -dbtype nucl -parse_seqids", shell=True)
    # Remove fasta file
    os.remove(target_fa)

    # Blast query against target db
    df = blast_to_df(query_fa, db, 90, 90)
    print(tabulate(df, headers='keys', tablefmt='psql'))


def blast_to_df(qry_pth, db_pth, id, cov):
    # BLAST query against target
    hdrs = ["qseqid", "sseqid", "pident", "qlen", "slen", "length", "qcovs",
            "qcovhsp", "mismatch", "gapopen", "evalue", "bitscore"]
    cmd = f"blastn -query {qry_pth} -db {db_pth} -perc_identity {id} -qcov_hsp_perc {cov} \
    -outfmt '6 {' '.join(hdrs)}'"
    # print(cmd)
    output = subprocess.check_output(cmd, shell=True, universal_newlines=True)
    outp_df = pd.read_csv(StringIO(output), sep='\t', names=hdrs)
    return outp_df


def get_fasta_from_api(file, limit=None):
    '''Gets list of dictionaries from DB view via API request,
    and writes this in fasta format, using supplied file name.
    Optionally limits number of view rows to include in fasta file.'''
    url = 'http://localhost:3000/app_asv_tax_seq'
    if limit:
        url = f'{url}?limit={limit}'
    r = requests.get(url, headers={'Accept': 'application/json'})
    asvs = json.loads(r.text)
    with open(file, 'w') as f:
        [f.write('>' + asv['asv_id'] + '-' + asv['higher_taxonomy'] +
                 '\n' + asv['asv_sequence'] + '\n') for asv in asvs]


if __name__ == '__main__':
    main()
