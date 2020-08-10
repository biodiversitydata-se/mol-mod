#!/usr/bin/env python

import os


def get_env_variable(name):
    try:
        return os.environ[name]
    except KeyError:
        message = "Expected environment variable '{}' not set.".format(name)
        raise Exception(message)


class Config:
    SECRET_KEY = get_env_variable('SECRET_KEY') or 'you-will-never-guess'
    DEBUG = False
    TESTING = False


class ProductionConfig(Config):
    pass


class DevelopmentConfig(Config):
    DEBUG = True
    BLAST_DB = 'misc/blastdb/asvdb'


class TestConfig(Config):
    TESTING = True


def get_config():
    try:
        env = get_env_variable('FLASK_ENV')
    except Exception:
        env = 'development'
        print('FLASK_ENV is not set, using FLASK_ENV:', env)

    if env == 'production':
        return ProductionConfig()
    elif env == 'test':
        return TestConfig()

    return DevelopmentConfig()
