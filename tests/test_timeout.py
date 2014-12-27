from flask.ext.celery import _select_manager
import pytest

from tests.instances import celery


@pytest.mark.parametrize('task_name,timeout', [
    ('tests.instances.mul', 20), ('tests.instances.add', 300), ('tests.instances.add2', 70),
    ('tests.instances.add3', 80)
])
def test_instances(task_name, timeout):
    manager_class = _select_manager(celery.backend.__class__.__name__)
    manager_instance = list()
    task = celery.tasks[task_name]
    original_exit = manager_class.__exit__

    def new_exit(self, *_):
        manager_instance.append(self)
        return original_exit(self, *_)
    setattr(manager_class, '__exit__', new_exit)
    task.apply_async(args=(4, 4)).get()
    setattr(manager_class, '__exit__', original_exit)
    assert timeout == manager_instance[0].timeout


@pytest.mark.parametrize('key,value', [('CELERYD_TASK_TIME_LIMIT', 200), ('CELERYD_TASK_SOFT_TIME_LIMIT', 100)])
def test_settings(key, value):
    celery.conf.update({key: value})
    manager_class = _select_manager(celery.backend.__class__.__name__)
    manager_instance = list()
    original_exit = manager_class.__exit__

    def new_exit(self, *_):
        manager_instance.append(self)
        return original_exit(self, *_)
    setattr(manager_class, '__exit__', new_exit)
    tasks = [
        ('tests.instances.mul', 20), ('tests.instances.add', value), ('tests.instances.add2', 70),
        ('tests.instances.add3', 80)
    ]

    for task_name, timeout in tasks:
        task = celery.tasks[task_name]
        task.apply_async(args=(4, 4)).get()
        assert timeout == manager_instance.pop().timeout
    setattr(manager_class, '__exit__', original_exit)

    celery.conf.update({key: None})
