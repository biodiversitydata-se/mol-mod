#!/usr/bin/env python

# Conda env vars:
# $CONDA_PREFIX/etc/conda/activate.d - & deactivate.d - /env_vars.sh

# Std lib
import os

def get_env_variable(name):
    try:
        return os.environ[name]
    except KeyError:
        message = "Expected environment variable '{}' not set.".format(name)
        raise Exception(message)

# Base config
class Config:
    # Used to encrypt pwds
    SECRET_KEY = get_env_variable('SECRET_KEY')
    # SESSION_COOKIE_NAME = get_env_variable('SESSION_COOKIE_NAME')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(Config):
    # To eg. auto-reload app when changes are detected
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = get_env_variable("DEV_DATABASE_URI")

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    SQLALCHEMY_DATABASE_URI = get_env_variable("PROD_DATABASE_URI")
