"""pytest configuration for all tests in all directories."""

import os
import time

from flask import Flask
import pytest

from flask.ext.celery import Celery, single_instance
from flask.ext.redis import Redis
from flask.ext.sqlalchemy import SQLAlchemy


def generate_config():
    """Generates a Flask config dict with settings for a specific broker based on an environment variable.

    To be merged into app.config.

    Returns:
    A dict to be fed into app.config.update().
    """
    config = dict()

    if os.environ.get('BROKER') == 'rabbit':
        config['CELERY_BROKER_URL'] = 'amqp://user:pass@localhost//'
    elif os.environ.get('BROKER') == 'redis':
        config['REDIS_URL'] = 'redis://localhost/1'
        config['CELERY_BROKER_URL'] = config['REDIS_URL']
    elif os.environ.get('BROKER') == 'redis_sock':
        config['REDIS_URL'] = 'redis+socket://redis.sock'
        config['CELERY_BROKER_URL'] = config['REDIS_URL']
    elif os.environ.get('BROKER') == 'mongo':
        config['CELERY_BROKER_URL'] = 'mongodb://user:pass@localhost/test'
    elif os.environ.get('BROKER') == 'couch':
        config['CELERY_BROKER_URL'] = 'couchdb://user:pass@localhost/test'
    elif os.environ.get('BROKER') == 'beanstalk':
        config['CELERY_BROKER_URL'] = 'beanstalk://user:pass@localhost/test'
    elif os.environ.get('BROKER') == 'iron':
        config['CELERY_BROKER_URL'] = 'ironmq://project:token@/test'
    else:
        if os.environ.get('BROKER') == 'mysql':
            config['SQLALCHEMY_DATABASE_URI'] = 'mysql://user:pass@localhost/test'
        elif os.environ.get('BROKER') == 'postgres':
            config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:pass@localhost/test'
        else:
            config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_database.sqlite'
        config['CELERY_BROKER_URL'] = 'sqla+' + config['SQLALCHEMY_DATABASE_URI']

    if 'CELERY_BROKER_URL' in config:
        config['CELERY_RESULT_BACKEND'] = config['CELERY_BROKER_URL']

    return config


def generate_context(config, result=True, eager=True):
    """Creates the Flask app context and initializes any extensions such as Celery, Redis, SQLAlchemy, etc.

    Positional arguments:
    config -- partial Flask config dict from generate_config().

    Keyword arguments:
    result -- leave 'CELERY_RESULT_BACKEND' set in app.config. Default True.
    eager -- sets 'CELERY_ALWAYS_EAGER' to True.

    Returns:
    The Flask app instance.
    """
    if not result:
        config.pop('CELERY_RESULT_BACKEND', None)
    if eager:
        config['CELERY_ALWAYS_EAGER'] = True

    app = Flask(__name__)
    app.config.update(config)
    app.config['TESTING'] = True
    Celery(app)

    if 'SQLALCHEMY_DATABASE_URI' in app.config:
        db = SQLAlchemy(app)
        db.create_all()
    elif 'REDIS_URL' in app.config:
        Redis(app)

    return app


@pytest.fixture(scope='session')
def get_app():
    return lambda result, eager: generate_context(generate_config(), result=result, eager=eager)


@pytest.fixture(scope='session')
def get_tasks():

    def generate_tasks(app):
        """Generates and registers three Celery tasks upon this function's call.

        Positional arguments:
        app -- Flask application instance.

        Returns:
        Dictionary of Celery tasks. Keys are names and values are task definitions.
        """
        celery = app.extensions['celery'].celery

        @celery.task(bind=True)
        @single_instance
        def add(x, y):
            return x + y

        @celery.task(bind=True)
        @single_instance(include_args=True)
        def mul(x, y):
            return x * y

        @celery.task(bind=True)
        @single_instance
        def sub(x, y):
            time.sleep(1)
            return x + y

        return dict(add=add, mul=mul, sub=sub)

    return generate_tasks
