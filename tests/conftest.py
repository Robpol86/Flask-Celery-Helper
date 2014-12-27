"""pytest configuration for all tests in all directories."""

import threading
import time

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
    for i in range(20):  # Wait for worker to finish initializing to avoid a race condition I've been experiencing.
        if celery.finalized:
            break
        time.sleep(1)
