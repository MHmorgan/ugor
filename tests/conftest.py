import os
import tempfile

import pytest
from app import create_app, db


@pytest.fixture()
def app():
    db_file = f'{tempfile.gettempdir()}/ugor.db'
    app = create_app({
        'DATABASE': db_file
    })

    yield app

    os.remove(db_file)


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()
