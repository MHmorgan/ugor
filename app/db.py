import sqlite3
from pathlib import Path

from flask import current_app as app, g

__dir__ = [
    'close',
    'execute_script',
    'get_con',
    'get_meta',
    'init',
    'set_meta',
    'table_exists',

    # Attributes
    'conn',
]


def __getattr__(name):
    if name == 'conn':
        return get_conn()
    raise AttributeError(f'module {__name__} has no attribute {name}')


def get_conn() -> sqlite3.Connection:
    if 'db' not in g:
        sqlite3.threadsafety = 2
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db


def close(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()


def init():
    if not (p := Path(app.config['DATABASE'])).exists() \
            and app.config['DATABASE'] != ':memory:':
        p.touch()
    execute_script('schema.sql')

    try:
        v = int(get_meta('schema_version'))
    except ValueError:
        v = -1

    if v < app.config['SCHEMA']:
        set_meta('schema_version', app.config['SCHEMA'])


def get_meta(key) -> str:
    conn = get_conn()
    cur = conn.execute('SELECT value FROM Meta WHERE key = ?', (key,))
    if row := cur.fetchone():
        return row['value']
    return ''


def set_meta(key, value):
    conn = get_conn()
    conn.execute("INSERT OR REPLACE INTO Meta (key, value) VALUES (?, ?)", (key, value))
    conn.commit()


def table_exists(name) -> bool:
    conn = get_conn()
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?", (name,))
    return bool(cur.fetchone())


def execute_script(fname):
    conn = get_conn()
    with app.open_resource('sql/' + fname) as f:
        conn.executescript(f.read().decode('utf8'))
