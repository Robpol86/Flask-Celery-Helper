"""Test flask_celery.single_instance()."""

import pytest

from flask.ext.celery import CELERY_LOCK


@pytest.mark.parametrize('result', (True, False))
def test_basic(get_app, get_tasks, result):
    """Test task to make sure it works before testing instance decorator."""
    app = get_app(result=result, eager=True)
    add_task = get_tasks(app)['add']
    expected = 8
    actual = add_task.apply(args=(4, 4)).get()
    assert expected == actual


@pytest.mark.parametrize('result', (True, False))
def test_instance(get_app, get_tasks, result):
    """Test for exception to be raised."""
    # Prepare.
    app = get_app(result=result, eager=True)
    add_task = get_tasks(app)['add']
    redis = app.extensions['redis'].redis
    redis_key = CELERY_LOCK.format(task_name='tests.conftest.add')
    lock = redis.lock(redis_key, timeout=1)
    have_lock = lock.acquire(blocking=False)
    assert True == bool(have_lock)
    # Test.
    with pytest.raises(RuntimeError) as e:
        add_task.apply(args=(4, 4)).get()
    assert 'Failed to acquire lock.' == str(e.value)
    lock.release()


@pytest.mark.parametrize('result', (True, False))
def test_instance_include_args(get_app, get_tasks, result):
    """Same as test_instance() but with single_instance(include_args=True)."""
    # Prepare.
    app = get_app(result=result, eager=True)
    mul_task = get_tasks(app)['mul']
    redis = app.extensions['redis'].redis
    redis_key = CELERY_LOCK.format(task_name='tests.conftest.mul.args.3d6442056c1bdf824b13ee277b62050c')
    lock = redis.lock(redis_key, timeout=1)
    have_lock = lock.acquire(blocking=False)
    assert True == bool(have_lock)
    # Test with different args.
    assert 12 == mul_task.apply(args=(4, 3)).get()
    # Test with matching.
    with pytest.raises(RuntimeError) as e:
        mul_task.apply(args=(4, 4)).get()
    assert 'Failed to acquire lock.' == str(e.value)
    lock.release()
