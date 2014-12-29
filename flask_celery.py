"""Celery support for Flask without breaking PyCharm inspections.

https://github.com/Robpol86/Flask-Celery-Helper
https://pypi.python.org/pypi/Flask-Celery-Helper
"""

from datetime import datetime, timedelta
from functools import partial, wraps
import hashlib
from logging import getLogger

from celery import _state, Celery as CeleryClass

__author__ = '@Robpol86'
__license__ = 'MIT'
__version__ = '1.1.0'


class OtherInstanceError(Exception):
    """Raised when Celery task is already running, when lock exists and has not timed out."""
    pass


class _LockManager(object):
    """Base class for other lock managers."""

    def __init__(self, celery_self, timeout, include_args, args, kwargs):
        """May raise NotImplementedError if the Celery backend is not supported.

        Positional arguments:
        celery_self -- from wrapped() within single_instance(). It is the `self` object specified in a binded Celery
            task definition (implicit first argument of the Celery task when @celery.task(bind=True) is used).
        timeout -- lock's timeout value in seconds.
        include_args -- if single instance should take arguments into account (boolean).
        args -- the task instance's args.
        kwargs -- the task instance's kwargs.
        """
        self.celery_self = celery_self
        self.timeout = timeout
        self.include_args = include_args
        self.args = args
        self.kwargs = kwargs
        self.log = getLogger('{0}:{1}'.format(self.__class__.__name__, self.task_identifier))

    @property
    def task_identifier(self):
        """Returns the unique identifier (string) of a task instance."""
        task_id = self.celery_self.name
        if self.include_args:
            merged_args = str(self.args) + str([(k, self.kwargs[k]) for k in sorted(self.kwargs)])
            task_id += '.args.{0}'.format(hashlib.md5(merged_args.encode('utf-8')).hexdigest())
        return task_id


class _LockManagerRedis(_LockManager):
    """Handles locking/unlocking for Redis backends."""

    CELERY_LOCK = '_celery.single_instance.{task_id}'

    def __init__(self, celery_self, timeout, include_args, args, kwargs):
        super(_LockManagerRedis, self).__init__(celery_self, timeout, include_args, args, kwargs)
        self.lock = None

    def __enter__(self):
        redis_key = self.CELERY_LOCK.format(task_id=self.task_identifier)
        self.lock = self.celery_self.backend.client.lock(redis_key, timeout=self.timeout)
        self.log.debug('Timeout %ds | Redis key %s', self.timeout, redis_key)
        if not self.lock.acquire(blocking=False):
            self.log.debug('Another instance is running.')
            raise OtherInstanceError('Failed to acquire lock, {0} already running.'.format(self.task_identifier))
        else:
            self.log.debug('Got lock, running.')

    def __exit__(self, exc_type, *_):
        if exc_type == OtherInstanceError:
            # Failed to get lock last time, not releasing.
            return
        self.log.debug('Releasing lock.')
        self.lock.release()

    @property
    def is_already_running(self):
        """Returns True if lock exists and has not timed out."""
        redis_key = self.CELERY_LOCK.format(task_id=self.task_identifier)
        return self.celery_self.backend.client.exists(redis_key)

    def reset_lock(self):
        """Removed the lock regardless of timeout."""
        redis_key = self.CELERY_LOCK.format(task_id=self.task_identifier)
        self.celery_self.backend.client.delete(redis_key)


class _LockManagerDB(_LockManager):
    """Handles locking/unlocking for SQLite/MySQL/PostgreSQL/etc backends."""

    def __init__(self, celery_self, timeout, include_args, args, kwargs):
        super(_LockManagerDB, self).__init__(celery_self, timeout, include_args, args, kwargs)
        self.save_group = getattr(self.celery_self.backend, '_save_group')
        self.restore_group = getattr(self.celery_self.backend, '_restore_group')
        self.delete_group = getattr(self.celery_self.backend, '_delete_group')

    def __enter__(self):
        self.log.debug('Timeout %ds', self.timeout)
        try:
            self.save_group(self.task_identifier, None)
        except Exception as exc:
            if 'IntegrityError' not in str(exc) and 'ProgrammingError' not in str(exc):
                raise
            difference = datetime.utcnow() - self.restore_group(self.task_identifier)['date_done']
            if difference < timedelta(seconds=self.timeout):
                self.log.debug('Another instance is running.')
                raise OtherInstanceError('Failed to acquire lock, {0} already running.'.format(self.task_identifier))
            self.log.debug('Timeout expired, stale lock found, releasing lock.')
            self.delete_group(self.task_identifier)
            self.save_group(self.task_identifier, None)
            self.log.debug('Got lock, running.')

    def __exit__(self, exc_type, *_):
        if exc_type == OtherInstanceError:
            # Failed to get lock last time, not releasing.
            return
        self.log.debug('Releasing lock.')
        self.delete_group(self.task_identifier)

    @property
    def is_already_running(self):
        """Returns True if lock exists and has not timed out."""
        date_done = (self.restore_group(self.task_identifier) or dict()).get('date_done')
        if not date_done:
            return False
        difference = datetime.utcnow() - date_done
        return difference < timedelta(seconds=self.timeout)

    def reset_lock(self):
        """Removed the lock regardless of timeout."""
        self.delete_group(self.task_identifier)


def _select_manager(backend_name):
    """Selects the proper LockManager based on the current backend used by Celery.

    Raises:
    NotImplementedError if Celery is using an unsupported backend.

    Positional arguments:
    backend -- Class name of the current Celery backend. Usually value of:
        current_app.extensions['celery'].celery.backend.__class__.__name__.

    Returns:
    Class definition object (not instance). One of the _LockManager* classes.
    """
    if backend_name == 'RedisBackend':
        lock_manager = _LockManagerRedis
    elif backend_name == 'DatabaseBackend':
        lock_manager = _LockManagerDB
    else:
        raise NotImplementedError
    return lock_manager


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
            app.extensions = dict()
        if 'celery' in app.extensions:
            raise ValueError('Already registered extension CELERY.')
        app.extensions['celery'] = _CeleryState(self, app)

        # Instantiate celery and read config.
        super(Celery, self).__init__(app.import_name, broker=app.config['CELERY_BROKER_URL'])

        # Set result backend default.
        if 'CELERY_RESULT_BACKEND' in app.config:
            self._preconf['CELERY_RESULT_BACKEND'] = app.config['CELERY_RESULT_BACKEND']

        self.conf.update(app.config)
        task_base = self.Task

        # Add Flask app context to celery instance.
        class ContextTask(task_base):
            """Celery instance wrapped within the Flask app context."""
            def __call__(self, *_args, **_kwargs):
                with app.app_context():
                    return task_base.__call__(self, *_args, **_kwargs)
        setattr(ContextTask, 'abstract', True)
        setattr(self, 'Task', ContextTask)


def single_instance(func=None, lock_timeout=None, include_args=False):
    """Celery task decorator. Forces the task to have only one running instance at a time.

    Use with binded tasks (@celery.task(bind=True)).

    Modeled after:
    http://loose-bits.com/2010/10/distributed-task-locking-in-celery.html
    http://blogs.it.ox.ac.uk/inapickle/2012/01/05/python-decorators-with-optional-arguments/

    Written by @Robpol86.

    Raises:
    OtherInstanceError -- if another instance is already running.

    Positional arguments:
    func -- the function to decorate, must be also decorated by @celery.task.

    Keyword arguments:
    lock_timeout -- lock timeout in seconds plus five more seconds, in-case the task crashes and fails to release the
        lock. If not specified, the values of the task's soft/hard limits are used. If all else fails, timeout will be 5
        minutes.
    include_args -- include the md5 checksum of the arguments passed to the task in the Redis key. This allows the same
        task to run with different arguments, only stopping a task from running if another instance of it is running
        with the same arguments.
    """
    if func is None:
        return partial(single_instance, lock_timeout=lock_timeout, include_args=include_args)

    @wraps(func)
    def wrapped(celery_self, *args, **kwargs):
        """Wrapped Celery task, for single_instance()."""
        # Select the manager and get timeout.
        timeout = (
            lock_timeout or celery_self.soft_time_limit or celery_self.time_limit
            or celery_self.app.conf.get('CELERYD_TASK_SOFT_TIME_LIMIT')
            or celery_self.app.conf.get('CELERYD_TASK_TIME_LIMIT')
            or (60 * 5)
        )
        manager_class = _select_manager(celery_self.backend.__class__.__name__)
        lock_manager = manager_class(celery_self, timeout, include_args, args, kwargs)

        # Lock and execute.
        with lock_manager:
            ret_value = func(*args, **kwargs)
        return ret_value
    return wrapped
