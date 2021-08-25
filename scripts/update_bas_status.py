#!/usr/bin/env python3
"""
This is a wrapper script to run status_updater.py inside a docker container.
To see arguments that can be passed on to the status updater, run:
docker exec -i asv-main ./molmod/importer/status_updater.py -h
"""

if __name__ == '__main__':

    import argparse
    import subprocess

    # Use docstring as help intro
    PARSER = argparse.ArgumentParser(description=__doc__)

    PARSER.add_argument("--container", default="asv-main",
                        help="Docker container to execute the updater "
                             "script in."
                        )

    # Parse above argument directly, and pass any additional to script
    ARGS, PASSED_ARGS = PARSER.parse_known_args()

    #
    # Compose cmd to execute script in container
    # Path refers to script location inside container
    #

    CMD = ["docker", "exec", "-i", ARGS.container,
           "./molmod/importer/status_updater.py"] + PASSED_ARGS

    subprocess.run(CMD)
