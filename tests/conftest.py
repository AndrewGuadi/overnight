import pytest, os
from app import create_app, extensions

@pytest.fixture
def app():
    os.environ['FLASK_ENV'] = 'testing'
    _app = create_app()
    _app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with _app.app_context():
        extensions.db.create_all()
        yield _app
