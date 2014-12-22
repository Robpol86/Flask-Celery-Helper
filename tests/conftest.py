"""pytest configuration for all tests in all directories."""

import threading

import pytest

from tests.instances import app, celery


class Worker(threading.Thread):
    def run(self):
        celery_args = ['-C', '-q', '-c', '1', '-P', 'solo', '--without-gossip']
        with app.app_context():
            celery.worker_main(celery_args)


@pytest.fixture(autouse=True, scope='session')
def celery_worker():
    """Starts the Celery worker in a background thread."""
    thread = Worker()
    thread.daemon = True
    thread.start()
