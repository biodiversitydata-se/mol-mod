#!/usr/bin/env python3
"""
This is a wrapper script to run (and pass arguments to) status_updater.py
inside a running container. To see those additional arguments, use:
`docker exec -i asv-main ./molmod/importer/status_updater.py -h`
(in development), or
`docker exec -i asv-main ./molmod/importer/status_updater.py -h`
(in production). Then add them to the wrapper command, e.g:
`./scripts/update_bas_status.py 13 1 -v --dry-run` (in development) or e.g.
`./scripts/update_bas_status.py --container asv-main 13 1 -v --dry-run`
(in production).
"""

if __name__ == '__main__':

    import argparse
    import subprocess

    #
    # Use argparse to execute this script using the command-line interpreter,
    # parse arguments into python object (ARGS), and compose help
    # (access with './scripts/update_bas_status.py -h' in molmod dir)
    #
    # Use docstring as help intro
    PARSER = argparse.ArgumentParser(description=__doc__)

    PARSER.add_argument("--container", default="asv-main",
                        help="Docker container to execute import script in. "
                             "Probably asv-main for production env."
                        )
    PARSER.add_argument("updater_args", nargs=argparse.REMAINDER,
                        help=("Additional arguments to pass to "
                              "updater script."))

    ARGS = PARSER.parse_args()

    #
    # Compose cmd to execute import.py in container
    # Path refers to script location inside container
    #

    CMD = ["docker", "exec", "-i", ARGS.container,
           "./molmod/importer/status_updater.py"] + ARGS.updater_args

    STATUS_UPDATER = subprocess.run(CMD)
