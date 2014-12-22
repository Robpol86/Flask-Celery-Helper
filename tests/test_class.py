import pytest

from flask.ext.celery import Celery


class FakeApp(object):
    config = dict(CELERY_BROKER_URL='redis://localhost', CELERY_RESULT_BACKEND='redis://localhost')
    static_url_path = ''
    import_name = ''

    def register_blueprint(self, _):
        pass


@pytest.mark.parametrize('result', (True, False))
def test_multiple(get_app, result):
    app = get_app(result=result, eager=True)
    assert 'celery' in app.extensions

    with pytest.raises(ValueError):
        Celery(app)


def test_one_dumb_line():
    app = FakeApp()
    Celery(app)
    assert 'celery' in app.extensions
