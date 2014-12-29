Flask-Celery-Helper
===================

Even though the `Flask documentation <http://flask.pocoo.org/docs/patterns/celery/>`_ says Celery extensions are
unnecessary now, I found that I still need an extension to properly use Celery in large Flask applications. Specifically
I need an init_app() method to initialize Celery after I instantiate it.

This extension also comes with a ``single_instance`` method.

* Python 2.6, 2.7, 3.3, and 3.4 supported on Linux and OS X.
* Python 2.7, 3.3, and 3.4 supported on Windows (both 32 and 64 bit versions of Python).

.. image:: https://img.shields.io/appveyor/ci/Robpol86/Flask-Celery-Helper.svg?style=flat-square
   :target: https://ci.appveyor.com/project/Robpol86/Flask-Celery-Helper
   :alt: Build Status Windows

.. image:: https://img.shields.io/travis/Robpol86/Flask-Celery-Helper/master.svg?style=flat-square
   :target: https://travis-ci.org/Robpol86/Flask-Celery-Helper
   :alt: Build Status

.. image:: https://img.shields.io/codecov/c/github/Robpol86/Flask-Celery-Helper/master.svg?style=flat-square
   :target: https://codecov.io/github/Robpol86/Flask-Celery-Helper
   :alt: Coverage Status

.. image:: https://img.shields.io/pypi/v/Flask-Celery-Helper.svg?style=flat-square
   :target: https://pypi.python.org/pypi/Flask-Celery-Helper/
   :alt: Latest Version

.. image:: https://img.shields.io/pypi/dm/Flask-Celery-Helper.svg?style=flat-square
   :target: https://pypi.python.org/pypi/Flask-Celery-Helper/
   :alt: Downloads

Attribution
-----------

Single instance decorator inspired by
`Ryan Roemer <http://loose-bits.com/2010/10/distributed-task-locking-in-celery.html>`_.

Supported Platforms
-------------------

* OSX and Linux.
* Python 2.6, 2.7, 3.3, 3.4
* `Flask <http://flask.pocoo.org/>`_ 0.10.1
* `Redis <http://redis.io/>`_ 2.9.1
* `Celery <http://www.celeryproject.org/>`_ 3.1.11

Quickstart
----------

Install:

.. code:: bash

    pip install Flask-Celery-Helper


Example:

.. code:: python

    # example.py
    from flask import Flask
    from flask.ext.celery import Celery
    
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
    from flask.ext.celery import Celery
    
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
    from flask.ext.celery import Celery, single_instance
    from flask.ext.redis import Redis
    
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


Changelog
---------

1.1.0
`````

* Added Windows support.
* ``CELERY_RESULT_BACKEND`` no longer mandatory.
* ``single_instance`` supported on SQLite/MySQL/PostgreSQL in addition to Redis.
* Breaking changes: ``flask.ext.celery.CELERY_LOCK`` moved to ``flask.ext.celery._LockManagerRedis.CELERY_LOCK``.

1.0.0
`````

* Support for non-Redis backends.

0.2.2
`````

* Added Python 2.6 and 3.x support.

0.2.1
`````

* Fixed ``single_instance`` arguments with functools.

0.2.0
`````

* Added include_args argument to ``single_instance``.

0.1.0
`````

* Initial release.
