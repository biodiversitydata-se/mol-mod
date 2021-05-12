#!/usr/bin/env python3

import os
import secrets


def get_env_variable(name: str):
    '''
    Gets env var or warns if missing
    '''
    try:
        return os.environ[name]
    except KeyError:
        message = "Expected environment variable '{}' not set.".format(name)
        raise Exception(message)


class Config:
    SECRET_KEY = secrets.token_hex()
    POSTGREST = get_env_variable('POSTGREST_HOST') or 'http://localhost:3000'
    BLAST_DB = get_env_variable('BLAST_DB')
    DEBUG = False
    TESTING = False
    # SBDI links
    SBDI_START_PAGE = get_env_variable('SBDI_START_PAGE')
    SBDI_CONTACT_PAGE = get_env_variable('SBDI_CONTACT_PAGE')
    SBDI_SEQ_SEARCH_PAGE = get_env_variable('SBDI_SEQ_SEARCH_PAGE')
    SBDI_MOLECULAR_PAGE = get_env_variable('SBDI_MOLECULAR_PAGE')
    BIOATLAS_PAGE = get_env_variable('BIOATLAS_PAGE')
    TAXONOMY_PAGE = get_env_variable('TAXONOMY_PAGE')
    # CAS authentication
    CAS_SERVER = get_env_variable('CAS_SERVER')
    CAS_AFTER_LOGIN = get_env_variable('CAS_AFTER_LOGIN')
    # Data submission
    UPLOAD_PATH = get_env_variable('UPLOAD_PATH')
    UPLOAD_ROLE = get_env_variable('UPLOAD_ROLE')
    MAX_CONTENT_LENGTH = int(get_env_variable('MAX_CONTENT_LENGTH'))
    VALID_EXTENSIONS = get_env_variable('VALID_EXTENSIONS').split(' ')

    # Cache settings (Flask internal), but see also molecular.config in proxy
    # (https://github.com/biodiversitydata-se/proxy-ws-mol-mod-docker)
    SEND_FILE_MAX_AGE_DEFAULT = 300  # 300 seconds = 5 minutes


class ProductionConfig(Config):
    DEBUG = False
    # For POST requests from search result forms to BioAtlas/SBDI
    BATCH_SEARCH_URL = 'https://records.biodiversitydata.se/' \
                       'ws/occurrences/batchSearch'
    REDIRECT_URL = 'https://records.biodiversitydata.se/occurrences/search'
    # For testing in local production env,
    # run or add this to your bash startup file (e.g. ~/.bash_profile):
    # export HOST_URL=http://localhost:5000
    CAS_AFTER_LOGOUT = get_env_variable('CAS_AFTER_LOGOUT') or \
        'https://molecular.biodiversitydata.se'


class DevelopmentConfig(Config):
    DEBUG = True
    # For POST requests from search result forms to BioAtlas/SBDI
    BATCH_SEARCH_URL = 'https://molecular.infrabas.se/' \
                       'biocache-service/occurrences/batchSearch'
    REDIRECT_URL = 'https://molecular.infrabas.se/ala-hub/occurrences/search'
    CAS_AFTER_LOGOUT = 'http://localhost:5000'


class TestConfig(Config):
    TESTING = True


def get_config():
    '''
    Uses FLASK_ENV (set in start.sh) to determine app environment.
    '''
    try:
        env = get_env_variable('FLASK_ENV')
    except Exception:
        env = 'development'
        print('FLASK_ENV is not set, using FLASK_ENV:', env)

    if env == 'production':
        return ProductionConfig()
    elif env == 'test':
        return TestConfig()

    # also set FLASK_DEBUG during development
    os.environ['FLASK_DEBUG'] = '1'

    return DevelopmentConfig()
