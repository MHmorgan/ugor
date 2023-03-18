import sqlite3
from functools import wraps
from os import environ

import arrow
from click import echo
from flask import (
    Flask,
    request,
    redirect,
)

from . import db, files
from .errors import AppError, NoSuchFile
from .files import File


def create_app(test_config=None):
    app = Flask(__name__, static_folder=None)

    app.secret_key = environ.get(
        'SECRET_KEY',
        '215d1e29a947cfb884b4692b27ca27bef8449f58365021d890b84bd22983133b'
    )
    app.config.update(
        VERSION='0.0',
        SCHEMA=0,
        DATABASE=environ.get('DATABASE', 'db.sqlite3'),
    )
    if test_config is not None:
        app.config.update(test_config)

    with app.app_context():
        db.init()
    app.teardown_appcontext(db.close)

    @app.cli.command('version')
    def version():
        """Display application/schema version."""
        echo(f'App version: {app.config["VERSION"]}')
        echo(f'Schema version: {app.config["SCHEMA"]}')

    ############################################################################
    # ROGU, INFO & FIND

    @app.get('/')
    def get_rogu():
        """Return the rogu executable."""
        return redirect('https://github.com/MHmorgan/rogu/releases/latest/download/rogu')

    @app.route('/', methods=['INFO'])
    def get_info():
        """Return application info."""
        return {'version': app.config['VERSION']}

    @app.route('/', methods=['FIND'], defaults={'path_prefix': ''})
    @app.route('/<path:path_prefix>', methods=['FIND'])
    @handle_errors
    def find_file(path_prefix):
        params = {
            pascal_to_snake(key): val
            for key, val in (request.get_json(silent=True) or {}).items()
        }
        find = files.Finder(path_prefix, **params)
        result = find()
        return result, 200 if result else 440

    ############################################################################
    # GET FILE

    @app.get('/<path:name>')
    @handle_errors
    def get_file(name):
        """Return a file."""

        file = files.fetch(name)

        headers = (
            ('Etag', file.etag),
            ('Last-Modified', file.modified),
            ('Content-Type', file.mime or 'application/octet-stream'),
            ('Content-Encoding', file.encoding),
            ('File-Description', file.description),
            ('File-Tag', file.tag),
            ('File-Tag2', file.tag2),
            ('File-Tag3', file.tag3),
            ('File-Data', file.data),
            ('File-Data2', file.data2),
            ('File-Data3', file.data3),
            ('File-Data4', file.data4),
            ('File-Data5', file.data5),
        )
        headers = {k: v for k, v in headers if v is not None}

        if modified := request.headers.get('If-Modified-Since'):
            t = arrow.get(modified)
            m = arrow.get(file.modified)
            if m <= t:
                return '', 304, headers

        # Since file.etag is "<hash>" (with quotes) this is pretty safe.
        if etags := request.headers.get('If-None-Match'):
            if file.etag in etags:
                return '', 304, headers

        return file.content, 200, headers

    ############################################################################
    # PUT FILE

    @app.put('/<path:name>')
    @handle_errors
    def write_file(name):
        """Create or update a file."""

        file = File.from_request(name, request)

        try:
            code = 204
            old = files.fetch(name)

            # Conditionals

            if etags := request.headers.get('If-Match'):
                if old.etag not in etags:
                    raise AppError('Etag mismatch', 412)

            if modified := request.headers.get('If-Unmodified-Since'):
                t = arrow.get(modified)
                m = arrow.get(old.modified)
                if m > t:
                    raise AppError('File modified', 412)

            # Merge old and new info

            if not file.mime and old.mime:
                file.mime = old.mime
            if not file.encoding and old.encoding:
                file.encoding = old.encoding

            for field, header in File.field_to_header().items():
                if header not in request.headers and (val := getattr(old, field)):
                    setattr(file, field, val)

        except NoSuchFile:
            code = 201

        try:
            if code == 201:
                files.create(file)
            else:
                files.update(file)

        except sqlite3.Error as e:
            # Not null constraint failed
            if e.sqlite_errorcode == 1299:
                raise AppError('Missing required data') from e
            else:
                raise e

        headers = {
            'Etag': file.etag,
            'Last-Modified': file.modified,
        }

        return '', code, headers

    ############################################################################
    # DELETE FILE

    @app.delete('/<path:name>')
    @handle_errors
    def delete_file(name):
        """Delete a file."""

        file = files.fetch(name)

        if etags := request.headers.get('If-Match'):
            if file.etag not in etags:
                raise AppError('Etag mismatch', 412)

        if modified := request.headers.get('If-Unmodified-Since'):
            t = arrow.get(modified)
            m = arrow.get(file.modified)
            if m > t:
                raise AppError('File modified', 412)

        files.delete(name)
        return '', 204

    return app


################################################################################
# UTILS

def handle_errors(f):
    """Decorator to handle exceptions gracefully."""

    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except AppError as e:
            return e.message, e.code

    return wrapper


def pascal_to_snake(s):
    return ''.join(['_' + c.lower() if c.isupper() else c for c in s]).lstrip('_')
