#!/usr/bin/env python

import csv
import json
import io
from io import StringIO
import subprocess
from subprocess import check_output

import pandas as pd
from tabulate import tabulate

seq = '>test1\nTGGGGAATATTGGGCAATGGAGGAAACTCTGACCCAGCGACGCCGCGTGCGGGATGAAGGCCTTCGGGTTGTAAACCGCTTTCAGCAGGGAAGAAGCGAAAGTGACGGTACCTGCAGAAGAAGCACCGGCTAACTATGTGCCAGCAGCCGCGGTAATACATAGGGTGCAAGCGTTGTCCGGAATTATTGGGCGTAAAGAGCTCGTAGGTGGTTCGTCACGTCGGATGTGAAACTCTGGGGCTTAACCCCAGACCTGCATTCGATACGGGCGAGCTTGAGTATGGTAGGGGAGTCTGGAATTCCTGGTGTAGCGGTGGAATGCGCAGATATCAGGAGGAACACCAATGGCGAAGGCAGGACTCTGGGCCATTACTGACACTGAGGAGCGAAAGCGTGGGGAGCGAACA'


def main():
    blast(seq)


def blast(seq):
    cmd = ['blastn']  # [form.blast_algorithm.data]

    e_val = int(10) * 10**int(-5)
    cmd += ["-evalue", str(e_val)]

    blast_db = "app/data/blastdb/asvdb"

    cmd += ['-db', blast_db]
    names = ['qacc', 'sacc', 'pident', 'length', 'evalue', 'bitscore']

    cmd += ['-outfmt', f'6 {" ".join(names)}']

    # Spawn system process and direct data to file handles
    with subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE) as process:
        # Send seq from form to stdin, read output & error until eof
        blast_stdout, stderr = process.communicate(input=seq.encode())
        # Get exit status
        returncode = process.returncode
    # print(returncode)

    # If OK
    if returncode == 0:
        # Make in-memory file-like str from blast-output
        with io.StringIO(blast_stdout.decode()) as stdout_buf:
            # Read into dataframe
            df = pd.read_csv(stdout_buf, sep='\t', index_col=0, header=None, names=names)

        # Filter on identity and alignment length
        df = df[df['pident'] >= 97]
        hits_after_pident = len(df)

        df = df[df['length'] >= 400]
        hits_after_length = len(df)

        print(tabulate(df))
        #
        # # Fetch counts for the matching genes
        # if len(df) == 0:
        #     msg = "No hits were found in the BLAST search"
        #     # flash(msg, category="error")
        #     return msg
        #
        # return render_template('blast_results.html',  tables=[df.to_html(classes='data')], title='BLAST hits', titles=df.columns.values)

#     msg = "Error, the BLAST query was not successful."
#     flash(msg, category="error")
#
#     # Logging the error
#     print("BLAST ERROR, cmd: {}".format(cmd))
#     print("BLAST ERROR, returncode: {}".format(returncode))
#     print("BLAST ERROR, output: {}".format(blast_stdout))
#     print("BLAST ERROR, stderr: {}".format(stderr))
#
#
# return render_template('blast.html', form=form)


if __name__ == '__main__':
    main()
