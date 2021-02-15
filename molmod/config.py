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


class ProductionConfig(Config):
    DEBUG = True
    # For POST requests from search result forms to BioAtlas/SBDI
    BATCH_SEARCH_URL = 'http://molecular.infrabas.se/' \
                       'biocache-service/occurrences/batchSearch'
    REDIRECT_URL = 'http://molecular.infrabas.se/ala-hub/occurrences/search'
    # PostgREST
    API_URL = 'http://localhost:3000'


class DevelopmentConfig(Config):
    DEBUG = True
    # For POST requests from search result forms to BioAtlas/SBDI
    BATCH_SEARCH_URL = 'http://molecular.infrabas.se/' \
                       'biocache-service/occurrences/batchSearch'
    REDIRECT_URL = 'http://molecular.infrabas.se/ala-hub/occurrences/search'
    # PostgREST
    API_URL = 'http://localhost:3000'


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
