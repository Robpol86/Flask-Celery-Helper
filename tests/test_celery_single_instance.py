"""Test flask_celery.single_instance()."""

import pytest

from flask.ext.celery import _LockManagerRedis, OtherInstanceError
from redis.exceptions import LockError

from tests.instances import app, celery


def test_basic():
    """Test task to make sure it works before testing instance decorator."""
    add_task = celery.tasks['tests.instances.add']
    expected = 8
    actual = add_task.apply_async(args=(4, 4)).get()
    assert expected == actual


def test_instance():
    """Test for exception to be raised."""
    # Prepare.
    add_task = celery.tasks['tests.instances.add']
    redis = app.extensions['redis'].redis
    redis_key = _LockManagerRedis.CELERY_LOCK_REDIS.format(task_id='tests.instances.add')
    lock = redis.lock(redis_key, timeout=1)
    have_lock = lock.acquire(blocking=False)
    assert True == bool(have_lock)
    # Test.
    with pytest.raises(OtherInstanceError) as e:
        add_task.apply_async(args=(4, 4)).get()
    assert 'Failed to acquire lock, tests.instances.add already running.' == str(e.value)
    lock.release()


def test_instance_include_args():
    """Same as test_instance() but with single_instance(include_args=True)."""
    # Prepare.
    mul_task = celery.tasks['tests.instances.mul']
    redis = app.extensions['redis'].redis
    redis_key = _LockManagerRedis.CELERY_LOCK_REDIS.format(
        task_id='tests.instances.mul.args.3d6442056c1bdf824b13ee277b62050c'
    )
    lock = redis.lock(redis_key, timeout=1)
    have_lock = lock.acquire(blocking=False)
    assert True == bool(have_lock)
    # Test with different args.
    assert 12 == mul_task.apply_async(args=(4, 3)).get()
    # Test with matching.
    with pytest.raises(OtherInstanceError) as e:
        mul_task.apply_async(args=(4, 4)).get()
    assert str(e.value).startswith('Failed to acquire lock, tests.instances.mul.args.')
    try:
        lock.release()
    except LockError:
        pass
