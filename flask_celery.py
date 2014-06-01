"""Celery support for Flask without breaking PyCharm inspections.

https://github.com/Robpol86/Flask-Celery-Helper
https://pypi.python.org/pypi/Flask-Celery-Helper
"""
from functools import wraps
from logging import getLogger

from celery import _state, Celery as CeleryClass
from flask import current_app


__author__ = '@Robpol86'
__license__ = 'MIT'
__version__ = '0.1.0'

CELERY_LOCK = '_celery.single_instance.{}'


class _CeleryState(object):
    """Remembers the configuration for the (celery, app) tuple. Modeled from SQLAlchemy."""

    def __init__(self, celery, app):
        self.celery = celery
        self.app = app


# noinspection PyProtectedMember
class Celery(CeleryClass):
    """Celery extension for Flask applications.

    Involves a hack to allow views and tests importing the celery instance from extensions.py to access the regular
    Celery instance methods. This is done by subclassing celery.Celery and overwriting celery._state._register_app()
    with a lambda/function that does nothing at all.

    That way, on the first super() in this class' __init__(), all of the required instance objects are initialized, but
    the Celery application is not registered. This class will be initialized in extensions.py but at that moment the
    Flask application is not yet available.

    Then, once the Flask application is available, this class' init_app() method will be called, with the Flask
    application as an argument. init_app() will again call celery.Celery.__init__() but this time with the
    celery._state._register_app() restored to its original functionality. in init_app() the actual Celery application is
    initialized like normal.
    """

    def __init__(self, app=None):
        """If app argument provided then initialize celery using application config values.

        If no app argument provided you should do initialization later with init_app method.

        Keyword arguments:
        app -- Flask application instance.
        """
        self.original_register_app = _state._register_app  # Backup Celery app registration function.
        _state._register_app = lambda _: None  # Upon Celery app registration attempt, do nothing.
        super(Celery, self).__init__()
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Actual method to read celery settings from app configuration and initialize the celery instance.

        Positional arguments:
        app -- Flask application instance.
        """
        _state._register_app = self.original_register_app  # Restore Celery app registration function.
        if not hasattr(app, 'extensions'):
            app.extensions = {}
        app.extensions['celery'] = _CeleryState(self, app)

        # Instantiate celery and read config.
        super(Celery, self).__init__(app.import_name, broker=app.config['REDIS_URL'])
        self._preconf['CELERY_RESULT_BACKEND'] = app.config['REDIS_URL']  # Set result backend default.
        self.conf.update(app.config)
        task_base = self.Task

        # Add Flask app context to celery instance.
        class ContextTask(task_base):
            def __call__(self, *_args, **_kwargs):
                with app.app_context():
                    return task_base.__call__(self, *_args, **_kwargs)
        setattr(ContextTask, 'abstract', True)
        setattr(self, 'Task', ContextTask)


def single_instance(func, lock_timeout=None):
    """Celery task decorator. Forces the task to have only one running instance at a time through locks set using Redis.
    Use with binded tasks (@celery.task(bind=True)).

    Modeled after:
    http://loose-bits.com/2010/10/distributed-task-locking-in-celery.html

    Written by @Robpol86.

    Positional arguments:
    func -- the function to decorate, must be also decorated by @celery.task.

    Keyword arguments:
    lock_timeout -- lock timeout in seconds plus five more seconds, in-case the task crashes and fails to release the
        lock. If not specified, the values of the task's soft/hard limits are used. If all else fails, timeout will be 5
        minutes.
    """
    @wraps(func)
    def wrapped(self, *args, **kwargs):
        log = getLogger('single_instance.wrapped')
        redis = current_app.extensions['redis'].redis
        ret_value, have_lock = None, False
        redis_key = CELERY_LOCK.format(self.name)
        time_limit = current_app.config.get('CELERYD_TASK_TIME_LIMIT')
        soft_time_limit = current_app.config.get('CELERYD_TASK_SOFT_TIME_LIMIT')
        timeout_ = lock_timeout or self.soft_time_limit or self.time_limit or soft_time_limit or time_limit or (60 * 5)
        lock = redis.lock(redis_key, timeout=(int(timeout_) + 5))
        log.debug('single_instance.wrapped({}.{}): Timeout {}s | Redis key {}'.format(func.__module__, func.func_name,
                timeout_, redis_key))
        # Done setting up, now run the function.
        try:
            have_lock = lock.acquire(blocking=False)
            if have_lock:
                log.debug('single_instance.wrapped({}.{}): Got lock, running.'.format(func.__module__, func.func_name))
                ret_value = func(*args, **kwargs)
            else:
                log.debug('single_instance.wrapped({}.{}): Another instance is running.'.format(func.__module__,
                        func.func_name))
                raise RuntimeError('Failed to acquire lock.')
        finally:
            if have_lock:
                log.debug('single_instance.wrapped({}.{}): Releasing lock.'.format(func.__module__, func.func_name))
                lock.release()
        return ret_value
    return wrapped
