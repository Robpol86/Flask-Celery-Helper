"""Test flask_celery.single_instance()."""

import pytest

from flask.ext.celery import _LockManagerRedis, OtherInstanceError, _select_manager
from redis.exceptions import LockError

from tests.instances import app, celery

PARAMS = [('tests.instances.add', 8), ('tests.instances.mul', 16), ('tests.instances.sub', 0)]

@pytest.mark.parametrize('task_name,expected', PARAMS)
def test_basic(task_name, expected):
    task = celery.tasks[task_name]
    assert expected == task.apply_async(args=(4, 4)).get()


@pytest.mark.parametrize('task_name,expected', PARAMS)
def test_collision(task_name, expected):
    manager_class = _select_manager(celery.backend.__class__.__name__)
    manager_instance = list()
    task = celery.tasks[task_name]

    # First run the task and prevent it from removing the lock.
    def new_exit(self, *_):
        manager_instance.append(self)
        return None
    original_exit = manager_class.__exit__
    setattr(manager_class, '__exit__', new_exit)
    assert expected == task.apply_async(args=(4, 4)).get()
    setattr(manager_class, '__exit__', original_exit)
    assert manager_instance[0].is_already_running is True

    # Now run it again.
    with pytest.raises(OtherInstanceError) as e:
        task.apply_async(args=(4, 4)).get()
    if manager_instance[0].include_args:
        assert str(e.value).startswith('Failed to acquire lock, {0}.args.'.format(task_name))
    else:
        assert 'Failed to acquire lock, {0} already running.'.format(task_name) == str(e.value)

    # Clean up.
    manager_instance[0].reset_lock()
    assert manager_instance[0].is_already_running is False

    # Once more.
    assert expected == task.apply_async(args=(4, 4)).get()


def test_instance():
    """Test for exception to be raised."""
    # Prepare.
    add_task = celery.tasks['tests.instances.add']
    redis = app.extensions['redis'].redis
    redis_key = _LockManagerRedis.CELERY_LOCK.format(task_id='tests.instances.add')
    lock = redis.lock(redis_key, timeout=1)
    have_lock = lock.acquire(blocking=False)
    assert have_lock is True
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
    redis_key = _LockManagerRedis.CELERY_LOCK.format(
        task_id='tests.instances.mul.args.3d6442056c1bdf824b13ee277b62050c'
    )
    lock = redis.lock(redis_key, timeout=1)
    have_lock = lock.acquire(blocking=False)
    assert have_lock is True
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
