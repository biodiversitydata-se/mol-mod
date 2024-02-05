#!/usr/bin/env python3
"""
"""

if __name__ == '__main__':

    import argparse
    import subprocess

    # Use docstring as help intro
    PARSER = argparse.ArgumentParser(description=__doc__)

    PARSER.add_argument("--container", default="asv-main",
                        help="Docker container to execute the script in."
                        )

    # Parse above argument directly, and pass any additional to script
    ARGS, EXPORTER_ARGS = PARSER.parse_known_args()

    #
    # Compose cmd to execute script in container
    # Path refers to script location inside container
    #

    CMD = ["docker", "exec", "-i", ARGS.container,
           "./molmod/exporter/exporter.py"] + EXPORTER_ARGS

    subprocess.run(CMD)
