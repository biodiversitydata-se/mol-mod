#!/usr/bin/env python3
"""
This is a wrapper script to send an Excel data stream (and additional
arguments) to importer.py inside a running docker container.
To see arguments that can be passed on to the importer, run:
docker exec -i asv-main ./molmod/importer/importer.py -h
"""

if __name__ == '__main__':

    import argparse
    import logging
    import subprocess

    # Use docstring as help intro
    PARSER = argparse.ArgumentParser(description=__doc__)

    PARSER.add_argument("excel_file",
                        help="Excel file to insert data into database from."
                        )

    PARSER.add_argument("--container", default="asv-main",
                        help="Docker container to execute import script in. "
                             "Probably asv-main for production env."
                        )

    # Parse above argument directly, and pass any additional to script
    ARGS, IMPORTER_ARGS = PARSER.parse_known_args()

    #
    # Compose cmd to execute import.py in container
    # Path refers to script location inside container
    #

    CMD = ["docker", "exec", "-i", ARGS.container,
           "./molmod/importer/importer.py"] + IMPORTER_ARGS

    try:
        subprocess.run(CMD, stdin=open(ARGS.excel_file))
    except FileNotFoundError:
        logging.error("Could not find input file %s", ARGS.excel_file)
    except IsADirectoryError:
        logging.error("This is not an Excel or compressed tar file %s",
                      ARGS.excel_file)
