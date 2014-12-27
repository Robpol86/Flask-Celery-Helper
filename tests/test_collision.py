from flask.ext.celery import OtherInstanceError, _select_manager
import pytest

from tests.instances import celery

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
    assert manager_instance[0].is_already_running is True

    # Clean up.
    manager_instance[0].reset_lock()
    assert manager_instance[0].is_already_running is False

    # Once more.
    assert expected == task.apply_async(args=(4, 4)).get()


def test_include_args():
    manager_class = _select_manager(celery.backend.__class__.__name__)
    manager_instance = list()
    task = celery.tasks['tests.instances.mul']

    # First run the tasks and prevent them from removing the locks.
    def new_exit(self, *_):
        """Expected to be run twice."""
        manager_instance.append(self)
        return None
    original_exit = manager_class.__exit__
    setattr(manager_class, '__exit__', new_exit)
    assert 16 == task.apply_async(args=(4, 4)).get()
    assert 20 == task.apply_async(args=(5, 4)).get()
    setattr(manager_class, '__exit__', original_exit)
    assert manager_instance[0].is_already_running is True
    assert manager_instance[1].is_already_running is True

    # Now run them again.
    with pytest.raises(OtherInstanceError) as e:
        task.apply_async(args=(4, 4)).get()
    assert str(e.value).startswith('Failed to acquire lock, tests.instances.mul.args.')
    assert manager_instance[0].is_already_running is True
    with pytest.raises(OtherInstanceError) as e:
        task.apply_async(args=(5, 4)).get()
    assert str(e.value).startswith('Failed to acquire lock, tests.instances.mul.args.')
    assert manager_instance[1].is_already_running is True

    # Clean up.
    manager_instance[0].reset_lock()
    assert manager_instance[0].is_already_running is False
    manager_instance[1].reset_lock()
    assert manager_instance[1].is_already_running is False

    # Once more.
    assert 16 == task.apply_async(args=(4, 4)).get()
    assert 20 == task.apply_async(args=(5, 4)).get()
