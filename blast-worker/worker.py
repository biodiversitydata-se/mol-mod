#!/usr/bin/env python3
"""
Simple web server that accepts requests to run blast jobs. The worker tries to
keep track of the current number of jobs in case we would want to limit this in
the future.
"""

import json
import os
import subprocess
from logging.config import dictConfig

from flask import Flask, jsonify, request

#
# Start server
#

# Figure out environment to set log config
environment = os.getenv('RUN_ENV')
if environment != 'production':
    environment = 'development'

# Load log config, and create log before flask app
# See note on log_config vs FLASK_DEBUG setting in __init__.py
log_config = json.load(open(f'log/log_config_{environment}.json'))
dictConfig(log_config)

APP = Flask(__name__)
APP.jobs = 0


def unlist(value):
    """
    If given value is a list, it returns the first list entry,
    otherwise it returns the value.
    """
    return value[0] if isinstance(value, list) else value


@APP.route('/status')
def status():
    """
    Returns the current status of the worker
    """
    return jsonify(jobs=APP.jobs)


@APP.route('/', methods=['POST'])
def main():
    """
    Composes a BLAST command from a (DataTable) AJAX request, forwarded from
    molmod endpoint /blast_run, and executes the command using subprocess.
    """

    #
    # Format the BLAST command - return an error if the input form is missing
    # required values.
    #

    try:
        form = request.json

        field_names = ['qacc', 'stitle', 'pident', 'qcovhsp', 'evalue']

        # Collect BLAST cmd items into list
        cmd = ['blastn']
        cmd += ['-perc_identity', unlist(form['min_identity'])]
        # Query cover per High-Scoring Pair
        cmd += ['-qcov_hsp_perc', unlist(form['min_qry_cover'])]
        cmd += ['-db', os.path.join('/blastdbs', form['db'])]
        cmd += ['-outfmt', f'6 {" ".join(field_names)}']
        # Only report best High Scorting Pair per query/subject pair
        cmd += ['-max_hsps', '1']
        cmd += ['-num_threads', '4']

    except KeyError as err:
        # pylint: disable=no-member
        APP.logger.error(f'Command formatting resulted in: {err}')
        return str(err), 500

    #
    # Execute BLAST search using subprocess.
    #

    APP.jobs += 1
    APP.logger.debug(f'Job count is {APP.jobs}')

    try:
        with subprocess.Popen(cmd, stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE) as process:
            # Send seq from sform to stdin, read output & error until 'eof'
            stdout, stderr = process.communicate(
                input="\n".join(form['sequence']).encode()
            )

    # Make sure to catch everything so that workers can keep working
    # pylint: disable=broad-except
    except Exception as ex:
        # pylint: disable=no-member
        APP.logger.error("Subprocess error: %s", ex)
        return str(ex), 500

    else:
        # If BLAST returns success response
        if process.returncode == 0:
            # pylint: disable=no-member
            APP.logger.debug('BLAST success')

            #
            # Format results as JSON, to make it easier to parse.
            #

            raw = stdout.decode()
            results = []
            for row in raw.split('\n'):
                row = row.strip()
                if not row:
                    continue
                # Format as dictionary using list of field names,
                # transforming numerical strings into numbers
                result = {}
                for i, field in enumerate(row.split("\t")):
                    try:
                        value = float(field)
                    except ValueError:
                        value = field
                    try:
                        result[field_names[i]] = value
                    except Exception:
                        APP.logger.error(
                            f"Could not assign field {i} of {field_names}"
                            f" for row: {row}."
                        )
                results += [result]

            return jsonify(data=results)

        # If BLAST returns error (even if subprocess worked),
        # e.g. 2: Error in BLAST database
        err = stderr.decode()
        # pylint: disable=no-member
        APP.logger.error("%s", err.strip())
        return err, 500

    # Decrease job count, irrespective of success or failure
    finally:
        APP.jobs -= 1
        APP.logger.debug(f'Final job count is {APP.jobs}')
