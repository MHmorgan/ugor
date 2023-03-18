CREATE TABLE IF NOT EXISTS Meta
(
    key   TEXT PRIMARY KEY,
    value TEXT
) WITHOUT ROWID;


CREATE TABLE IF NOT EXISTS Files
(
    name        TEXT PRIMARY KEY,
    content          NOT NULL,

    etag             NOT NULL,
    modified    TEXT NOT NULL,
    mime        TEXT,
    encoding    TEXT,

    description TEXT,
    tag         TEXT,
    tag2        TEXT,
    tag3        TEXT,
    data        TEXT,
    data2       TEXT,
    data3       TEXT,
    data4       TEXT,
    data5       TEXT
) WITHOUT ROWID;


CREATE VIEW IF NOT EXISTS FindView AS
SELECT name,
       length(content)     AS size,
       unixepoch(modified) AS modified,
       mime,
       encoding,
       tag,
       tag2,
       tag3
FROM Files;
