#!/usr/bin/env python3
"""
This is a wrapper script to run the BLAST database builder inside the docker
container.
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

    PARSER.add_argument("--container", default="mol-mod_blast-worker_1",
                        help=("Docker container to execute the blast build "
                              "script in.")
                        )
    ARGS, BUILDER_ARGS = PARSER.parse_known_args()

    #
    # Compose cmd to execute import.py in container
    #

    CMD = ["docker", "exec", "-i", ARGS.container,
           "./blast_builder/blast_builder.py"] + BUILDER_ARGS

    BUILDER = subprocess.run(CMD)
