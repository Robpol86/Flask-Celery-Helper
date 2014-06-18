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


def test_instance_include_args(mul_task):
  """Same as test_instance() but with single_instance(include_args=True)."""
  # Prepare.
  redis = current_app.extensions['redis'].redis
  redis_key = CELERY_LOCK.format(task_name='tests.conftest.mul.args.3d6442056c1bdf824b13ee277b62050c')
  lock = redis.lock(redis_key, timeout=1)
  have_lock = lock.acquire(blocking=False)
  assert True == bool(have_lock)
  # Test with different args.
  assert 12 == mul_task.apply(args=(4, 3)).get()
  # Test with matching.
  with pytest.raises(RuntimeError) as e:
    mul_task.apply(args=(4, 4)).get()
  assert 'Failed to acquire lock.' == e.value.message
  lock.release()
