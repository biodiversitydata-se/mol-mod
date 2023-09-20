#!/usr/bin/env python3
"""
Collects environment variables set in .env(.template) to create distinct
configuration classes for running the main app in different contexts.
Also provides a function to select the corrrect class, based on the value of
RUN_ENV, which in turn is supplied in the dockerfile.
Finally, handles config of email used to send notification of uploaded files
"""

import os
import secrets


def get_env_variable(name: str):
    """
    Gets env var or warns if missing
    """
    try:
        return os.environ[name]
    except KeyError:
        message = "Expected environment variable '{}' not set.".format(name)
        raise Exception(message)


def load_config_values(target: object, filename: str):
    """
    Reads all variables from a secret / config file, formatted like:
      key1 = value
      key2 = value
      [...]
    and sets the loaded key/value pairs in the 'target' object.
    """
    with open(filename) as f:
        for row in f:
            row = row.strip()
            if not row or row[0] == '#':
                continue
            key, value = row.split("=")
            # format values so that boolean values and integers are parsed into
            # the correct type.
            value = value.strip().strip("'\"")  # remove whitespace and quotes
            # parse boolean
            if value.lower() in ['true', 't']:
                value = True
            elif value.lower() in ['false', 'f']:
                value = False
            # parse integers
            else:
                value = int(value) if value.isnumeric() else value

            setattr(target, key.strip(), value)


def to_list(raw: str) -> list:
    """If the 'raw' string is formatted like a list, it is converted to a list,
    otherwise returns a list with 'raw' as the single item.
    """
    raw = raw.strip()
    retval = []

    if raw[0] == '[' and raw[-1] == ']':
        for item in raw[1:-1].split(','):
            retval += [item.strip().strip("'\"")]
    else:
        retval += [raw]

    return retval


class Config:
    SECRET_KEY = secrets.token_hex()
    POSTGREST = get_env_variable('POSTGREST_HOST')
    BLAST_DB = get_env_variable('BLAST_DB')
    TESTING = False
    SBDI_START_PAGE = get_env_variable('SBDI_START_PAGE')
    SBDI_CONTACT_PAGE = get_env_variable('SBDI_CONTACT_PAGE')
    TAXONOMY_PAGE = get_env_variable('TAXONOMY_PAGE')
    ENA_GUIDE_PAGE = get_env_variable('ENA_GUIDE_PAGE')
    AMPLISEQ_PAGE = get_env_variable('AMPLISEQ_PAGE')
    IPT_BASE_URL = get_env_variable('IPT_BASE_URL')
    CAS_SERVER = get_env_variable('CAS_SERVER')
    CAS_AFTER_LOGIN = get_env_variable('CAS_AFTER_LOGIN')
    UPLOAD_PATH = get_env_variable('UPLOAD_PATH')
    UPLOAD_ROLE = get_env_variable('UPLOAD_ROLE')
    MAX_CONTENT_LENGTH = int(get_env_variable('MAX_CONTENT_LENGTH'))
    VALID_EXTENSIONS = get_env_variable('VALID_EXTENSIONS').split(' ')
    SEND_FILE_MAX_AGE_DEFAULT = int(get_env_variable(
        'SEND_FILE_MAX_AGE_DEFAULT'))
    SQLALCHEMY_SILENCE_UBER_WARNING = int(get_env_variable(
        'SQLALCHEMY_SILENCE_UBER_WARNING'))

    def __init__(self, config_file: str = "/run/secrets/email_config"):
        """
        Loads the email config values.
        """
        # Flask-Mail settings
        load_config_values(self, config_file)

        # Make sure that UPLOAD_EMAIL is a list
        self.UPLOAD_EMAIL = to_list(self.UPLOAD_EMAIL)


class ProductionConfig(Config):
    BATCH_SEARCH_URL = get_env_variable('BATCH_SEARCH_URL')
    REDIRECT_URL = get_env_variable('REDIRECT_URL')
    CAS_AFTER_LOGOUT = get_env_variable('CAS_AFTER_LOGOUT')
    UPLOAD_EMAIL = get_env_variable('UPLOAD_EMAIL')


class DevelopmentConfig(Config):
    BATCH_SEARCH_URL = get_env_variable('TEST_BATCH_SEARCH_URL')
    REDIRECT_URL = get_env_variable('TEST_REDIRECT_URL')
    CAS_AFTER_LOGOUT = get_env_variable('CAS_AFTER_LOGOUT')
    UPLOAD_EMAIL = get_env_variable('DEV_UPLOAD_EMAIL')


class TestConfig(Config):
    TESTING = True


def get_config():
    """
    Uses RUN_ENV (set in dockerfile) to determine app environment.
    """
    try:
        env = get_env_variable('RUN_ENV')
    except Exception:
        env = 'production'
        print('RUN_ENV is not set, using RUN_ENV:', env)

    if env == 'production':
        return ProductionConfig()
    elif env == 'test':
        return TestConfig()

    return DevelopmentConfig()
