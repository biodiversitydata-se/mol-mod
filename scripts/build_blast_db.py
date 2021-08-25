#!/usr/bin/env python3
"""
This is a wrapper script to run blast_builder.py inside a docker container.
To see arguments that can be passed on to the BLAST builder, run:
docker exec -i mol-mod_blast-worker_1 ./blast_builder/blast_builder.py -h
"""

if __name__ == '__main__':

    import argparse
    import subprocess

    # Use docstring as help intro
    PARSER = argparse.ArgumentParser(description=__doc__)

    PARSER.add_argument("--container", default="mol-mod_blast-worker_1",
                        help="Docker container to execute the blast build "
                             "script in."
                        )
    # Parse above argument directly, and pass any additional to script
    ARGS, BUILDER_ARGS = PARSER.parse_known_args()

    #
    # Compose cmd to execute script in container
    # Path refers to script location inside container
    #

    CMD = ["docker", "exec", "-i", ARGS.container,
           "./blast_builder/blast_builder.py"] + BUILDER_ARGS

    subprocess.run(CMD)
