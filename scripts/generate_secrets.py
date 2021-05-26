#!/usr/bin/env python3
"""
Script to generate the secrets needed for deployment. These secrets are:
 - postgres database password (in .secret.postgres_pass)
 - postgres anon password (in .secret.anon_pass)
 - postgrest config file (in .secret.postgrest_config)
"""

import logging
import os
import secrets
import sys


def generate_secret(filename, skip_existing: bool = False):
    """
    Generates single secret value (using `secrets.token_hex()`) and saves it
    as given `filename`. The permissions of the filename will be set to 400.

    If `skip_existing` is set, the function will just return the content of the
    currently existing file.
    """

    if skip_existing and os.path.isfile(filename):
        logging.info("secrets file %s already exists, skipping", filename)
        return open(filename).read()

    logging.info("generating secret token")
    secret = secrets.token_hex()

    try:
        with open(filename, 'w') as secret_file:
            secret_file.write(secret)
    except PermissionError:
        logging.error("Secret token already stored in %s.\nPlease, "
                      "delete all '.secret.*' files to generate new secrets, "
                      "or use --skip-existing arg to reuse old.", filename)
        sys.exit(1)
    else:
        logging.info("writing secret token to %s", filename)
        logging.info("setting permissions to 0444 for %s", filename)
        os.chmod(filename, 0o444)

        return secret


def write_config(config_file, template_file, skip_existing=False, **variables):
    """
    Reads the `template_file`, replaces variables formatted like <var> with the
    content in `variables`.

    ex. <user> gets replaces with the content of `user`.
        "<user>" -> "postgres"

    """

    if skip_existing and os.path.isfile(config_file):
        logging.info("secrets file %s already exists, skipping", config_file)
        return

    # load template
    template = open(template_file).read()

    logging.info('updating template variables')
    for variable, val in variables.items():
        start = template.find(f'<{variable}>')
        if start < 0:
            logging.warning("variable '%s' not found in template", variable)
            continue
        template = list(template)
        template[start:start+len(variable)+2] = val
        template = ''.join(template)

    with open(config_file, 'w') as config:
        logging.info("writing template file")
        config.write(template)

    logging.info("setting permissions to 0444 for %s", config_file)
    os.chmod(config_file, 0o444)


if __name__ == '__main__':

    import argparse

    PARSER = argparse.ArgumentParser(description=__doc__)

    PARSER.add_argument('-e', '--env', default='.env',
                        help="environment file for non-secret variables")
    PARSER.add_argument('-t', '--template',
                        default='config/postgrest.conf.template',
                        help="postgrest config template file")
    PARSER.add_argument('-m', '--email',
                        default='config/email.conf.template',
                        help="email config template file")
    PARSER.add_argument('--skip-existing', action="store_true",
                        help="Skip existing secrets")
    PARSER.add_argument('-v', '--verbose', action="count", default=0,
                        help="Increase logging verbosity (default: warning).")
    PARSER.add_argument('-q', '--quiet', action="count", default=3,
                        help="Decrease logging verbosity (default: warning).")

    ARGS = PARSER.parse_args()

    logging.basicConfig(level=(10*(ARGS.quiet - ARGS.verbose)))
    # E.g. -vv -> (30-10*2=10) debug, -q -> (30+10*1=40) error

    PG_PASS = generate_secret('.secret.postgres_pass', ARGS.skip_existing)
    PG_ANON = generate_secret('.secret.anon_pass', ARGS.skip_existing)
    PG_IPT = generate_secret('.secret.ipt_pass', ARGS.skip_existing)

    # read template file
    for row in open(ARGS.env):
        if row[0] == '#':
            continue
        if '=' in row:
            var, value = row.split('=')
            os.environ[var.strip()] = value.strip()

    # create dict of variables for the template
    VARS = {'user': os.getenv('POSTGRES_USER', 'postgres'),
            'passwd': PG_PASS,
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': os.getenv('POSTGRES_PORT', '5432'),
            'name': os.getenv('POSTGRES_DB', 'db')
            }

    write_config('.secret.postgrest_config', ARGS.template, ARGS.skip_existing,
                 **VARS)

    # Never overwrite email config
    write_config('.secret.email_config', ARGS.email, True)
