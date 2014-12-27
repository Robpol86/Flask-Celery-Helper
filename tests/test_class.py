from flask.ext.celery import Celery
import pytest

from tests.instances import app


class FakeApp(object):
    config = dict(CELERY_BROKER_URL='redis://localhost', CELERY_RESULT_BACKEND='redis://localhost')
    static_url_path = ''
    import_name = ''

    def register_blueprint(self, _):
        pass


def test_multiple():
    assert 'celery' in app.extensions

    with pytest.raises(ValueError):
        Celery(app)


def test_one_dumb_line():
    flask_app = FakeApp()
    Celery(flask_app)
    assert 'celery' in flask_app.extensions
