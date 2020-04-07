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
    # SESSION_COOKIE_NAME = get_env_variable('SESSION_COOKIE_NAME')
    # SQLALCHEMY_TRACK_MODIFICATIONS = False


class DevelopmentConfig(Config):
    # To eg. auto-reload app when changes are detected
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = get_env_variable("DEV_DATABASE_URI")


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    SQLALCHEMY_DATABASE_URI = get_env_variable("PROD_DATABASE_URI")
