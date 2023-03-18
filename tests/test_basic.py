from time import sleep

import arrow


def test_info(app, client):
    """Test Ugor info method."""

    response = client.open('/', method='INFO')
    assert response.status_code == 200
    assert response.json['version'] == app.config['VERSION']


def test_rogu(client):
    """Test rogu endpoint."""

    response = client.get('/')
    assert response.status_code == 302


def test_basic1(client):
    """Test basic functionality without headers."""

    path = '/test.txt'
    data = b'Lorem Ipsum'

    # PUT new

    response01 = client.put(path, data=data)
    assert response01.status_code == 201
    assert 'Etag' in response01.headers
    assert 'Last-Modified' in response01.headers

    # GET

    response02 = client.get(path)
    assert response02.status_code == 200

    assert 'Etag' in response02.headers
    assert 'Last-Modified' in response02.headers
    assert 'Content-Length' in response02.headers
    assert 'Content-Type' in response02.headers
    assert 'Content-Encoding' not in response02.headers
    assert 'File-Description' not in response02.headers
    assert 'File-Tag' not in response02.headers
    assert 'File-Tag2' not in response02.headers
    assert 'File-Tag3' not in response02.headers
    assert 'File-Data' not in response02.headers
    assert 'File-Data2' not in response02.headers
    assert 'File-Data3' not in response02.headers
    assert 'File-Data4' not in response02.headers
    assert 'File-Data5' not in response02.headers

    assert response02.headers['Content-Length'] == str(len(data))
    assert response02.headers['Content-Type'] == 'application/octet-stream'
    assert response02.data == data

    assert response02.headers['Etag'] == response01.headers['Etag']
    assert response02.headers['Last-Modified'] == response01.headers['Last-Modified']

    # PUT update

    data2 = data + b' 2'
    response03 = client.put(path, data=data2)
    assert response03.status_code == 204
    assert response01.headers['Etag'] != response03.headers['Etag']
    assert response01.headers['Last-Modified'] != response03.headers['Last-Modified']

    # GET updated

    response04 = client.get(path)
    assert response04.status_code == 200
    assert response04.headers['Etag'] == response03.headers['Etag']
    assert response04.headers['Last-Modified'] == response03.headers['Last-Modified']
    assert response04.data == data2

    # DELETE

    r = client.delete(path)
    assert r.status_code == 204

    # GET deleted

    r = client.get(path)
    assert r.status_code == 404


def test_basic2(client):
    """Test basic functionality with headers."""

    path = '/test.txt'
    data = b'Lorem Ipsum'

    # PUT new

    headers01 = {
        'Content-Type': 'text/plain',
        'Content-Encoding': 'gzip',
        'File-Description': 'Test file',
        'File-Tag': 'test',
        'File-Tag2': 'test2',
        'File-Tag3': 'test3',
        'File-Data': 'data',
        'File-Data2': 'data2',
        'File-Data3': 'data3',
        'File-Data4': 'data4',
        'File-Data5': 'data5',
    }
    response01 = client.put(path, data=data, headers=headers01)
    assert response01.status_code == 201
    assert 'Etag' in response01.headers
    assert 'Last-Modified' in response01.headers

    # GET

    response02 = client.get(path)
    assert response02.status_code == 200
    assert response02.data == data

    for key in headers01:
        assert key in response02.headers
        assert response02.headers[key] == headers01[key]

    # PUT update

    headers02 = {
        'Content-Type': 'text/html',
        'Content-Encoding': 'base64',
        'File-Description': 'Test file 2',
        'File-Tag': 'test2',
        'File-Tag2': 'test2-2',
        'File-Tag3': 'test2-3',
        'File-Data4': '',
        'File-Data5': '',
    }
    data2 = data + b' 2'
    response03 = client.put(path, data=data2, headers=headers02)
    assert response03.status_code == 204

    # GET updated

    response04 = client.get(path)
    assert response04.status_code == 200
    assert response04.data == data2

    # Updated headers
    for key in ('Content-Type', 'Content-Encoding', 'File-Description', 'File-Tag', 'File-Tag2', 'File-Tag3'):
        assert response04.headers[key] == headers02[key]
    # Unchanged headers
    for key in ('File-Data', 'File-Data2', 'File-Data3'):
        assert response04.headers[key] == headers01[key]
    # Removed headers
    assert 'File-Data4' not in response04.headers
    assert 'File-Data5' not in response04.headers


def test_basic3(client):
    """Test basic functionality with conditional headers."""
    time01 = arrow.utcnow().isoformat()

    path = '/test.txt'
    data = b'Lorem Ipsum'

    # PUT new

    response = client.put(path, data=data)
    assert response.status_code == 201
    assert 'Etag' in response.headers
    assert 'Last-Modified' in response.headers

    sleep(1)
    time02 = arrow.utcnow().isoformat()
    etag01 = response.headers['Etag']

    # GET with conditionals

    response = client.get(path, headers={'If-Modified-Since': time01})
    assert response.status_code == 200
    response = client.get(path, headers={'If-Modified-Since': time02})
    assert response.status_code == 304
    assert 'Etag' in response.headers

    response = client.get(path, headers={'If-None-Match': [etag01, '"123"']})
    assert response.status_code == 304
    assert 'Etag' in response.headers
    response = client.get(path, headers={'If-None-Match': '"123"'})
    assert response.status_code == 200

    # PUT update with conditionals

    data += b' 2'

    response = client.put(path, data=data, headers={'If-Unmodified-Since': time01})
    assert response.status_code == 412
    response = client.put(path, data=data, headers={'If-Unmodified-Since': time02})
    assert response.status_code == 204

    etag02 = response.headers['Etag']

    response = client.put(path, data=data, headers={'If-Match': etag01})
    assert response.status_code == 412
    response = client.put(path, data=data, headers={'If-Match': (etag01, etag02)})
    assert response.status_code == 204

    time03 = arrow.utcnow().isoformat()

    # DELETE with conditionals

    response = client.delete(path, headers={'If-Match': (etag01, '"123"')})
    assert response.status_code == 412
    response = client.delete(path, headers={'If-Unmodified-Since': time02})
    assert response.status_code == 412
    response = client.delete(path, headers={'If-Unmodified-Since': time03})
    assert response.status_code == 204


def test_find(client):
    """Test find method."""

    from functools import partial
    find = partial(client.open, method='FIND')

    def check(path, names, status=200, **kwargs):
        resp = find(path, **kwargs)
        assert resp.status_code == status
        assert sorted(resp.json) == sorted(names)
        return resp

    def create(path, **kwargs):
        resp = client.put(path, **kwargs)
        assert resp.status_code == 201
        # Wait a second to make sure the next file has a different timestamp.
        sleep(1)
        return resp

    # TEST FILES

    data = b'Lorem Ipsum'
    data2 = b'In a hole in the ground there lived a hobbit.'
    data3 = b'It is a truth universally acknowledged, that a single man in possession of a good fortune, must be in want of a wife.'

    r = create('/testfile', data=data)

    t1 = r.headers['Last-Modified']

    create('/peter.txt', data=data2, headers={
        'Content-Type': 'text/plain',
        'Content-Encoding': 'gzip',
        'File-Tag': 'Griffin',
        'File-Tag2': 'Dad',
        'File-Tag3': 'Male',
        'File-Data': 'Peter Griffin',
        'File-Data2': 'Shut up Meg!',
        'File-Data3': 'Family Guy',
        'File-Data4': 'Once upon a time, in a galaxy far, far away...',
        'File-Data5': 'Lorem ipsum dolor sit amet, consectetur adipiscing elit.',
    })
    create('/louis.txt', data=data2, headers={
        'Content-Type': 'text/html',
        'Content-Encoding': 'gzip',
        'File-Tag': 'Griffin',
        'File-Tag2': 'Mom',
        'File-Tag3': 'Female',
        'File-Data': 'Louis Griffin',
        'File-Data2': 'Shut up Meg!',
        'File-Data3': 'Family Guy',
        'File-Data4': 'Once upon a time, in a galaxy far, far away...',
        'File-Data5': 'Lorem ipsum dolor sit amet, consectetur adipiscing elit.',
    })
    create('/children/meg.txt', data=data, headers={'File-Tag2': 'Griffin'})
    r = create('/children/chris.txt', data=data3, headers={'File-Tag3': 'Griffin'})

    t2 = r.headers['Last-Modified']
    t3 = arrow.utcnow().isoformat()

    # FIND by path

    check('/', ['testfile', 'peter.txt', 'louis.txt', 'children/meg.txt', 'children/chris.txt'])
    check('/', ['testfile', 'peter.txt', 'louis.txt'], json={'recursive': False})
    check('/testfile', ['testfile'])
    check('/children', ['children/meg.txt', 'children/chris.txt'])
    check('/dontexist', [], status=440)

    # FIND by name

    check('/', ['peter.txt', 'louis.txt', 'children/meg.txt', 'children/chris.txt'], json={'name': '*.txt'})
    check('/', ['peter.txt', 'louis.txt'], json={'name': '*.txt', 'recursive': False})
    check('/', ['children/meg.txt', 'children/chris.txt'], json={'name': 'children/*.txt'})
    check('/children', ['children/meg.txt', 'children/chris.txt'], json={'name': '*.txt'})

    check('/', ['peter.txt', 'louis.txt', 'children/meg.txt', 'children/chris.txt'], json={'nameRe': r'.*\.txt'})
    check('/', ['peter.txt', 'louis.txt'], json={'nameRe': r'[^/]*\.txt'})
    check('/', [], status=440, json={'nameRe': r'\d+'})

    # FIND by tag

    check('/', ['peter.txt', 'louis.txt', 'children/meg.txt', 'children/chris.txt'], json={'tag': 'Griffin'})
    check('/children', ['children/meg.txt', 'children/chris.txt'], json={'tag': 'Griffin'})

    check('/', ['peter.txt', 'louis.txt'], json={'tag1': 'Griffin'})
    check('/', ['peter.txt'], json={'tag': 'Griffin', 'tag2': 'Dad'})
    check('/', ['louis.txt'], json={'tag3': 'Female'})

    # FIND by encoding

    check('/', ['peter.txt', 'louis.txt'], json={'encoding': 'gzip'})
    check('/children', [], status=440, json={'encoding': 'gzip'})

    # FIND by content type

    check('/', ['peter.txt', 'louis.txt'], json={'mime': 'text/*'})
    check('/', [], status=440, json={'mime': 'application/*'})

    # FIND by modified

    check('/children', ['children/chris.txt'], json={'modified': t2})
    check('/', ['peter.txt', 'louis.txt', 'children/meg.txt', 'children/chris.txt'], json={'modAfter': t1})
    check('/', ['testfile', 'peter.txt', 'louis.txt', 'children/meg.txt', 'children/chris.txt'], json={'modBefore': t3})
    check('/', [], status=440, json={'modified': t3})

    # FIND by size

    check('/', ['peter.txt', 'louis.txt'], json={'size': len(data2)})
    check('/', ['peter.txt', 'louis.txt', 'children/chris.txt'], json={'sizeGt': len(data)})
    check('/', ['testfile', 'children/meg.txt'], json={'sizeLt': len(data2)})
    check('/children', [], status=440, json={'size': len(data2)})
