import requests
import time

def test_unknown_id_gives_404():
    response : requests.Response = requests.get('http://127.0.0.1:5000/hellowait/lol1taa')

    assert response.status_code == 404
    assert response.json() == {'exists': False, 'result': None}


def test_works_correctly():
    response : requests.Response = requests.get('http://127.0.0.1:5000/hello')

    # submission happened ok
    assert response.status_code == 202
    assert response.json()["status"] == "Task has been submitted"

    # immediate status is pending
    task_id = response.json()["task_id"]
    response : requests.Response = requests.get(f'http://127.0.0.1:5000/hellowait/{task_id}')

    assert response.status_code == 200
    assert response.json() == {'exists': True, 'result': None}

    time.sleep(11)

    # after 11 secs we have the result
    response : requests.Response = requests.get(f'http://127.0.0.1:5000/hellowait/{task_id}')

    assert response.status_code == 200
    assert response.json() == {'exists': True, 'result': "Hello, World!"}

    # if we rerun, it is forgotten
    response : requests.Response = requests.get(f'http://127.0.0.1:5000/hellowait/{task_id}')

    assert response.status_code == 404
    assert response.json() == {'exists': False, 'result': None}