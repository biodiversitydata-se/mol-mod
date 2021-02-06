#!/usr/bin/env python3
"""
This is a wrapper script to send data to the data importer inside the asv-main
docker-container.
"""

import sys
import subprocess

if __name__ == '__main__':

    import argparse

    PARSER = argparse.ArgumentParser(description=__doc__)

    PARSER.add_argument("excel_file",
                        help="Excel file to insert data into the database from."
                        )

    PARSER.add_argument("--container", default="asv-main",
                        help="Docker container to execute the import script."
                        )
    PARSER.add_argument("importer_args", nargs=argparse.REMAINDER,
                        help=("All additional arguments will be passed to the "
                              "importer script."))

    ARGS = PARSER.parse_args()

    CMD = ["docker", "exec", "-i", ARGS.container,
           "./molmod/importer/import.py"] + ARGS.importer_args

    IMPORTER = subprocess.run(CMD, stdin=open(ARGS.excel_file))

