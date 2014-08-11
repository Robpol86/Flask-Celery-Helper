"""pytest configuration for all tests in all directories."""
from flask import current_app, Flask
import pytest

from flask.ext.celery import Celery, single_instance
from flask.ext.redis import Redis


@pytest.fixture(autouse=True, scope='session')
def app_context(request):
    """Initializes the application and sets the app context to avoid needing 'with app.app_context():'.

    This needs to run first, so it has been placed in the top-level conftest.py and the function starts with the letter
    'a'.
    """
    app = Flask(__name__)
    app.config['CELERY_ALWAYS_EAGER'] = True
    app.config['TESTING'] = True
    app.config['REDIS_URL'] = 'redis://localhost/1'
    Celery(app)
    Redis(app)
    context = app.app_context()
    context.push()
    request.addfinalizer(lambda: context.pop())


@pytest.fixture(scope='session')
def add_task():
    celery = current_app.extensions['celery'].celery

    @celery.task(bind=True)
    @single_instance
    def add(x, y):
        return x + y

    return add


@pytest.fixture(scope='session')
def mul_task():
    celery = current_app.extensions['celery'].celery

    @celery.task(bind=True)
    @single_instance(include_args=True)
    def mul(x, y):
        return x * y

    return mul
