#!/usr/bin/env python3
"""
This is a wrapper script to send an Excel data stream
to the data importer inside the asv-main docker-container.
"""

import subprocess

if __name__ == '__main__':

    import argparse

    PARSER = argparse.ArgumentParser(description=__doc__)

    PARSER.add_argument("excel_file",
                        help="Excel file to insert data into database from."
                        )

    PARSER.add_argument("--container", default="asv-main",
                        help="Docker container to execute import script in."
                        )
    PARSER.add_argument("importer_args", nargs=argparse.REMAINDER,
                        help=("Additional arguments to pass to "
                              "importer script."))

    ARGS = PARSER.parse_args()

    CMD = ["docker", "exec", "-i", ARGS.container,
           "./molmod/importer/import.py"] + ARGS.importer_args

    IMPORTER = subprocess.run(CMD, stdin=open(ARGS.excel_file))
