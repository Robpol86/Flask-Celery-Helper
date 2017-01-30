===================
Flask-Celery-Helper
===================

Even though the `Flask documentation <http://flask.pocoo.org/docs/patterns/celery/>`_ says Celery extensions are
unnecessary now, I found that I still need an extension to properly use Celery in large Flask applications. Specifically
I need an init_app() method to initialize Celery after I instantiate it.

This extension also comes with a ``single_instance`` method.

* Python 2.6, 2.7, PyPy, 3.3, and 3.4 supported on Linux and OS X.
* Python 2.7, 3.3, and 3.4 supported on Windows (both 32 and 64 bit versions of Python).

.. image:: https://img.shields.io/appveyor/ci/Robpol86/Flask-Celery-Helper/master.svg?style=flat-square&label=AppVeyor%20CI
    :target: https://ci.appveyor.com/project/Robpol86/Flask-Celery-Helper
    :alt: Build Status Windows

.. image:: https://img.shields.io/travis/Robpol86/Flask-Celery-Helper/master.svg?style=flat-square&label=Travis%20CI
    :target: https://travis-ci.org/Robpol86/Flask-Celery-Helper
    :alt: Build Status

.. image:: https://img.shields.io/codecov/c/github/Robpol86/Flask-Celery-Helper/master.svg?style=flat-square&label=Codecov
    :target: https://codecov.io/gh/Robpol86/Flask-Celery-Helper
    :alt: Coverage Status

.. image:: https://img.shields.io/pypi/v/Flask-Celery-Helper.svg?style=flat-square&label=Latest
    :target: https://pypi.python.org/pypi/Flask-Celery-Helper
    :alt: Latest Version

Attribution
===========

Single instance decorator inspired by
`Ryan Roemer <http://loose-bits.com/2010/10/distributed-task-locking-in-celery.html>`_.

Supported Libraries
===================

* `Flask <http://flask.pocoo.org/>`_ 0.12
* `Redis <http://redis.io/>`_ 3.2.6
* `Celery <http://www.celeryproject.org/>`_ 3.1.11

Quickstart
==========

Install:

.. code:: bash

    pip install Flask-Celery-Helper

Examples
========

Basic Example
-------------

.. code:: python

    # example.py
    from flask import Flask
    from flask_celery import Celery

    app = Flask('example')
    app.config['CELERY_BROKER_URL'] = 'redis://localhost'
    app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost'
    celery = Celery(app)

    @celery.task()
    def add_together(a, b):
        return a + b

    if __name__ == '__main__':
        result = add_together.delay(23, 42)
        print(result.get())

Run these two commands in separate terminals:

.. code:: bash

    celery -A example.celery worker
    python example.py

Factory Example
---------------

.. code:: python

    # extensions.py
    from flask_celery import Celery

    celery = Celery()

.. code:: python

    # application.py
    from flask import Flask
    from extensions import celery

    def create_app():
        app = Flask(__name__)
        app.config['CELERY_IMPORTS'] = ('tasks.add_together', )
        app.config['CELERY_BROKER_URL'] = 'redis://localhost'
        app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost'
        celery.init_app(app)
        return app

.. code:: python

    # tasks.py
    from extensions import celery

    @celery.task()
    def add_together(a, b):
        return a + b

.. code:: python

    # manage.py
    from application import create_app

    app = create_app()
    app.run()

Single Instance Example
-----------------------

.. code:: python

    # example.py
    import time
    from flask import Flask
    from flask_celery import Celery, single_instance
    from flask_redis import Redis

    app = Flask('example')
    app.config['REDIS_URL'] = 'redis://localhost'
    app.config['CELERY_BROKER_URL'] = 'redis://localhost'
    app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost'
    celery = Celery(app)
    Redis(app)

    @celery.task(bind=True)
    @single_instance
    def sleep_one_second(a, b):
        time.sleep(1)
        return a + b

    if __name__ == '__main__':
        task1 = sleep_one_second.delay(23, 42)
        time.sleep(0.1)
        task2 = sleep_one_second.delay(20, 40)
        results1 = task1.get(propagate=False)
        results2 = task2.get(propagate=False)
        print(results1)  # 65
        if isinstance(results2, Exception) and str(results2) == 'Failed to acquire lock.':
            print('Another instance is already running.')
        else:
            print(results2)  # Should not happen.

.. changelog-section-start

Changelog
=========

This project adheres to `Semantic Versioning <http://semver.org/>`_.

Unreleased
----------

Changed
    * Supporting Flask 0.12, switching from ``flask.ext.celery`` to ``flask_celery`` import recommendation.

1.1.0 - 2014-12-28
------------------

Added
    * Windows support.
    * ``single_instance`` supported on SQLite/MySQL/PostgreSQL in addition to Redis.

Changed
    * ``CELERY_RESULT_BACKEND`` no longer mandatory.
    * Breaking changes: ``flask.ext.celery.CELERY_LOCK`` moved to ``flask.ext.celery._LockManagerRedis.CELERY_LOCK``.

1.0.0 - 2014-11-01
------------------

Added
    * Support for non-Redis backends.

0.2.2 - 2014-08-11
------------------

Added
    * Python 2.6 and 3.x support.

0.2.1 - 2014-06-18
------------------

Fixed
    * ``single_instance`` arguments with functools.

0.2.0 - 2014-06-18
------------------

Added
    * ``include_args`` argument to ``single_instance``.

0.1.0 - 2014-06-01
------------------

* Initial release.

.. changelog-section-end
