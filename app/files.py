from dataclasses import dataclass, fields, asdict
from functools import cache
from hashlib import sha256

import arrow
import jinja2
from flask import Request

from . import db
from .errors import AppError, NoSuchFile

__dir__ = [
    'File',
    'Finder',
    'fetch',
    'create',
    'update',
    'delete',
]


################################################################################
#                                                                              #
# File class
#                                                                              #
################################################################################

@dataclass
class File:
    name: str
    content: bytes

    etag: str
    modified: str
    mime: str = None
    encoding: str = None

    description: str = None
    tag: str = None
    tag2: str = None
    tag3: str = None
    data: str = None
    data2: str = None
    data3: str = None
    data4: str = None
    data5: str = None

    @classmethod
    def from_row(cls, row):
        return cls(*row)

    @classmethod
    def from_request(cls, name: str, request: Request):
        kwargs = dict(
            name=name,
            content=request.data,
            etag='"' + sha256(request.data).hexdigest() + '"',
            modified=arrow.utcnow().isoformat(),
            mime=request.content_type,
            encoding=request.content_encoding,

            # Automatically handle custom file headers
            # using the awesome dataclass fields.
            #
            # Header values are always strings or None.
            # An empty string may be used to clear a field.
            #
            **{
                field: request.headers.get(header) or None
                for field, header in File.field_to_header().items()
            }
        )
        return cls(**kwargs)

    def __len__(self):
        return len(self.content)

    @classmethod
    @cache
    def field_to_header(cls):
        """Return a mapping of field names to custom file header names."""
        ignore_fields = ('name', 'content', 'etag', 'modified', 'mime', 'encoding')
        return {
            field.name: f'File-{field.name.capitalize()}'
            for field in fields(cls)
            if field.name not in ignore_fields
        }


################################################################################
#                                                                              #
# Module methods
#                                                                              #
################################################################################


def fetch(name: str) -> File:
    """Fetch file from database.

    Raises NoSuchFile if file does not exist.
    """
    with db.conn as conn:
        cur = conn.execute('SELECT * FROM Files WHERE name = ?', (name,))
        if row := cur.fetchone():
            return File.from_row(row)
        raise NoSuchFile(name)


def create(file: File):
    """Create file in database.

    SQLite error codes (https://www.sqlite.org/rescode.html):

    1299: A NOT NULL constraint failed (required field is missing).
    1555: Primary key constraint failed (file already exists).
    """

    f = fields(file)
    names = ', '.join(field.name for field in f)
    values = ', '.join(f':{field.name}' for field in f)

    sql = f'INSERT INTO Files ({names}) VALUES ({values})'
    params = asdict(file)

    with db.conn as conn:
        conn.execute(sql, params)


def update(file: File):
    """Update file in database."""

    f = fields(file)
    assignments = ', '.join(f'{field.name} = :{field.name}' for field in f if field.name != 'name')

    sql = f'UPDATE Files SET {assignments} WHERE name = :name'
    params = asdict(file)

    with db.conn as conn:
        conn.execute(sql, params)


def delete(name: str):
    """Delete file from database.

    Will not raise an error if file does not exist.
    """
    with db.conn as conn:
        conn.execute('DELETE FROM Files WHERE name = ?', (name,))


################################################################################
#                                                                              #
# File finder
#                                                                              #
################################################################################

@dataclass
class Finder:
    path_prefix: str

    name: str = None
    name_re: str = None

    encoding: str = None
    mime: str = None
    size: int = None
    size_gt: int = None
    size_lt: int = None

    modified: str = None
    mod_before: str = None
    mod_after: str = None

    tag: str = None
    tag1: str = None
    tag2: str = None
    tag3: str = None

    recursive: bool = True

    def __post_init__(self):
        def invalid(msg):
            raise AppError(f'Invalid find parameters: {msg}')

        # Validate find parameters

        exclusive = (
            ('name', 'name_re'),
            ('size', 'size_gt', 'size_lt'),
            ('modified', 'mod_before', 'mod_after'),
        )
        for group in exclusive:
            if sum(1 for field in group if getattr(self, field) is not None) > 1:
                invalid(f'Cannot specify more than one of {", ".join(group)}')

    def __call__(self, *args, **kwargs) -> list[str]:
        """Return a list of file names matching the finder parameters."""

        import re

        sql = self.__FIND_TEMPLATE.render(**asdict(self))

        with db.conn as conn:
            cur = conn.execute(sql, asdict(self))
            names = [row[0] for row in cur.fetchall()]

        if not self.recursive and self.path_prefix is not None:
            names = [
                name for name in names
                if name.count('/') == self.path_prefix.count('/')
            ]

        if self.name_re:
            regex = re.compile(self.name_re)
            names = [name for name in names if regex.match(name)]

        return names

    __FIND_TEMPLATE = jinja2.Template('''
        SELECT name
        FROM FindView
        WHERE
        
        {%- if name %}
            name GLOB :name AND
        {%- endif %}
        
        {%- if encoding %}
            encoding = :encoding AND
        {%- endif %}
        
        {%- if mime %}
            mime GLOB :mime AND
        {%- endif %}
        
        {%- if size %}
            size = :size AND
        {%- elif size_gt %}
            size > :size_gt AND
        {%- elif size_lt %}
            size < :size_lt AND
        {%- endif %}
        
        {%- if modified %}
            modified = unixepoch(:modified) AND
        {%- elif mod_before %}
            modified < unixepoch(:mod_before) AND
        {%- elif mod_after %}
            modified > unixepoch(:mod_after) AND
        {%- endif %}
        
        {%- if tag %}
            :tag IN (tag, tag2, tag3) AND
        {%- endif %}
        
        {%- if tag1 %}
            tag = :tag1 AND
        {%- endif %}
        
        {%- if tag2 %}
            tag2 = :tag2 AND
        {%- endif %}
        
        {%- if tag3 %}
            tag3 = :tag3 AND
        {%- endif %}
        
        {%- if path_prefix %}
            name GLOB :path_prefix || '*';
        {%- else %}
            1;
        {%- endif %}
    ''')
