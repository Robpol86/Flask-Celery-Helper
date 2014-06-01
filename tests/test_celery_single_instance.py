"""Test flask_celery.single_instance()."""
from flask import current_app
from flask.ext.celery import Celery, CELERY_LOCK, single_instance
import pytest


CELERY = Celery(current_app)


@CELERY.task(bind=True)
@single_instance
def add(x, y):
  return x + y


@pytest.fixture(autouse=True, scope='session')
def register_tasks():
  CELERY.tasks.register(add)


def test_basic():
  """Test task to make sure it works before testing instance decorator."""
  expected = 8
  actual = add.apply(args=(4, 4)).get()
  assert expected == actual


def test_instance():
  """Test for exception to be raised."""
  # Prepare.
  redis = current_app.extensions['redis'].redis
  redis_key = CELERY_LOCK.format('tests.test_celery_single_instance.add')
  lock = redis.lock(redis_key, timeout=1)
  have_lock = lock.acquire(blocking=False)
  assert True == bool(have_lock)
  # Test.
  with pytest.raises(RuntimeError) as e:
    add.apply(args=(4, 4)).get()
  assert 'Failed to acquire lock.' == e.value.message
  lock.release()
