#!/usr/bin/env python

import os


def get_env_variable(name):
    try:
        return os.environ[name]
    except KeyError:
        message = "Expected environment variable '{}' not set.".format(name)
        raise Exception(message)


class Config:
    # Use hardcoded string if env. variable is missing
    SECRET_KEY = get_env_variable('SECRET_KEY') or 'you-will-never-guess'


class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = True


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
