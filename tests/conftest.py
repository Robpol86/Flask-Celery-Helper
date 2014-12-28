"""pytest configuration for all tests in all directories."""

import threading
import time

from celery.signals import worker_ready
import pytest

from tests.instances import app, celery

WORKER_READY = list()


class Worker(threading.Thread):
    def run(self):
        celery_args = ['-C', '-q', '-c', '1', '-P', 'solo', '--without-gossip']
        with app.app_context():
            celery.worker_main(celery_args)


@worker_ready.connect
def on_worker_ready(**_):
    """Called when the Celery worker thread is ready to do work.

    This is to avoid race conditions since everything is in one python process.
    """
    WORKER_READY.append(True)


@pytest.fixture(autouse=True, scope='session')
def celery_worker():
    """Starts the Celery worker in a background thread."""
    thread = Worker()
    thread.daemon = True
    thread.start()
    for i in range(10):  # Wait for worker to finish initializing to avoid a race condition I've been experiencing.
        if WORKER_READY:
            break
        time.sleep(1)
