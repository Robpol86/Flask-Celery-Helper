Flask-Celery-Helper
===================

Even though the [Flask documentation](http://flask.pocoo.org/docs/patterns/celery/) says Celery extensions are
unnecessary now, I found that I still need an extension to properly use Celery in large Flask applications. Specifically
I need an init_app() method to initialize Celery after I instantiate it.

This extension also comes with a `single_instance` method using Redis locks.

*Currently only works with Redis backends.*

Attribution
-----------

Single instance decorator inspired by
[Ryan Roemer](http://loose-bits.com/2010/10/distributed-task-locking-in-celery.html).

Supported Platforms
-------------------

* OSX and Linux.
* Python 2.7
* [Flask](http://flask.pocoo.org/) 0.10.1
* [Redis](http://redis.io/) 2.9.1
* [Celery](http://www.celeryproject.org/) 3.1.11

Probably works on other versions too.

Quickstart
----------

Install:
```bash
pip install Flask-Celery-Helper
```

Example:
```python
# example.py
from flask import Flask
from flask.ext.celery import Celery

app = Flask('example')
app.config['REDIS_URL'] = 'redis://localhost'
celery = Celery(app)

@celery.task()
def add_together(a, b):
    return a + b

if __name__ == '__main__':
    result = add_together.delay(23, 42)
    print(result.get())
```

Run these two commands in separate terminals:
```bash
celery -A example.celery worker
python example.py
```

Factory Example
---------------

```python
# extensions.py
from flask.ext.celery import Celery

celery = Celery()
```

```python
# application.py
from flask import Flask
from extensions import celery

def create_app():
    app = Flask(__name__)
    app.config['CELERY_IMPORTS'] = ('tasks.add_together', )
    app.config['REDIS_URL'] = 'redis://localhost'
    celery.init_app(app)
    return app
```

```python
# tasks.py
from extensions import celery

@celery.task()
def add_together(a, b):
    return a + b
```

```python
# manage.py
from application import create_app

app = create_app()
app.run()
```

Single Instance Example
-----------------------

```python
import time
from flask import Flask
from flask.ext.celery import Celery, single_instance

app = Flask(__name__)
app.config['REDIS_URL'] = 'redis://localhost'
celery = Celery(app)

@celery.task(bind=True)
@single_instance
def sleep_five_seconds(a, b):
    time.sleep(5)
    return a + b

task1 = sleep_five_seconds.delay(23, 42)
task2 = sleep_five_seconds.delay(20, 40)

results2 = task.get(propagate=False)
if isinstance(results2, Exception) and str(results2) == 'Failed to acquire lock.':
    print('Another instance is already running.')
else:
    print(results2)
print(result1.get())
```
