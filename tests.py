import pytest
import staticfuzz


@pytest.fixture
def app():

    return staticfuzz.app


def test_index_route(client):
    resp = client.get('/')
    assert resp.status_code == 200


def test_new_memory(client):
    resp = client.post('/new_memory', data={'text': '/danbooru goo_girl'},
                       follow_redirects=True)
    assert resp.status_code == 200
