"""Test flask_celery.single_instance()."""
from flask import current_app
from flask.ext.celery import CELERY_LOCK
import pytest


def test_basic(add_task):
  """Test task to make sure it works before testing instance decorator."""
  expected = 8
  actual = add_task.apply(args=(4, 4)).get()
  assert expected == actual


def test_instance(add_task):
  """Test for exception to be raised."""
  # Prepare.
  redis = current_app.extensions['redis'].redis
  redis_key = CELERY_LOCK.format(task_name='tests.conftest.add')
  lock = redis.lock(redis_key, timeout=1)
  have_lock = lock.acquire(blocking=False)
  assert True == bool(have_lock)
  # Test.
  with pytest.raises(RuntimeError) as e:
    add_task.apply(args=(4, 4)).get()
  assert 'Failed to acquire lock.' == e.value.message
  lock.release()
