import json


def test_insecure(webui):
    app = webui.test_client()

    assert app.get('/admin/').status_code == 200


def test_secure(webui_secure):
    app = webui_secure.test_client()

    def login(username, password):
        return app.post(
            '/users/login', data={'username': username, 'password': password})

    def is_admin():
        return json.loads(app.get('/users/is-admin').data)['is_admin']

    def get_users():
        return json.loads(app.get('/users/').data)['users']

    # Unauthenticated
    assert app.get('/admin/').status_code == 401

    # Admin
    assert login('admin', 'admin').status_code == 302

    assert app.get('/admin/').status_code == 200

    assert app.get('/users/').status_code == 200

    assert is_admin() is True

    assert get_users() == ['admin']

    user = app.post(
        '/users/add',
        data=json.dumps({'username': 'user'}), content_type='application/json')
    set_password = json.loads(user.data)['link']

    assert get_users() == ['admin', 'user']

    app.get('/users/logout')

    # User
    app.post(set_password, data={'username': 'user', 'password': 'user'})
    assert login('user', 'user').status_code == 302

    assert app.get('/admin/').status_code == 200

    assert app.get('/users/').status_code == 401

    assert is_admin() is False

    app.get('/users/logout')

    # Delete User

    assert login('admin', 'admin').status_code == 302

    assert get_users() == ['admin', 'user']

    app.post(
        '/users/delete',
        data=json.dumps({'username': 'user'}), content_type='application/json')

    assert get_users() == ['admin']
