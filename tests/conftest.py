"""pytest configuration for all tests in all directories."""
from flask import Flask
from flask.ext.redis import Redis
import pytest


@pytest.fixture(autouse=True, scope='session')
def app_context(request):
    """Initializes the application and sets the app context to avoid needing 'with app.app_context():' This needs to run
    first, so it has been placed in the top-level conftest.py and the function starts with the letter 'a'.
    """
    app = Flask(__name__)
    app.config['CELERY_ALWAYS_EAGER'] = True
    app.config['TESTING'] = True
    app.config['REDIS_URL'] = 'redis://localhost/1'
    Redis(app)
    context = app.app_context()
    context.push()
    request.addfinalizer(lambda: context.pop())
