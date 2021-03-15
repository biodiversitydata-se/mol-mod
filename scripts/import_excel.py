#!/usr/bin/env python3
"""
This is a wrapper script to send an Excel data stream
to the data importer inside a running asv-main docker-container.
"""

if __name__ == '__main__':

    import argparse
    import logging
    import subprocess

    #
    # Use argparse to execute this script using the command-line interpreter,
    # parse arguments into python object (ARGS), and compose help
    # (access with './scripts/import_excel.py -h' in molmod dir)
    #
    # Use docstring as help intro
    PARSER = argparse.ArgumentParser(description=__doc__)

    PARSER.add_argument("excel_file",
                        help="Excel file to insert data into database from."
                        )

    PARSER.add_argument("--container", default="asv-main",
                        help="Docker container to execute import script in. "
                             "Probably mol-mod_asv-main_1 for production env."
                        )
    PARSER.add_argument("importer_args", nargs=argparse.REMAINDER,
                        help=("Additional arguments to pass to "
                              "importer script."))

    ARGS = PARSER.parse_args()

    #
    # Compose cmd to execute import.py in container
    #

    CMD = ["docker", "exec", "-i", ARGS.container,
           "./molmod/importer/importer.py"] + ARGS.importer_args

    try:
        IMPORTER = subprocess.run(CMD, stdin=open(ARGS.excel_file))
    except FileNotFoundError:
        logging.error("Could not find input file %s", ARGS.excel_file)
    except IsADirectoryError:
        logging.error("This is not an Excel or compressed tar file %s",
                      ARGS.excel_file)
