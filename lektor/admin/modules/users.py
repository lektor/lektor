import functools

import flask
from flask import Blueprint, g, redirect, url_for, current_app, request


bp = Blueprint('users', __name__, url_prefix='/users')


def _is_admin():
    from flask.ext.login import current_user
    return current_user.id == 1


def admin_required(func):
    @functools.wraps(func)
    def decorated_view(*args, **kwargs):
        if not _is_admin():
            return current_app.login_manager.unauthorized()
        return func(*args, **kwargs)
    return decorated_view


def set_password_link(tmp_token):
    return url_for('users.set_password', tmp_token=tmp_token, _external=True)


@bp.record_once
def init(state):
    app = state.app
    project = app.lektor_info.env.project

    if project.database_uri:
        from flask.ext import login
        from flask.ext.login import login_user, logout_user, current_user

        from flask.ext.wtf import Form
        from wtforms import StringField, PasswordField, SubmitField

        with app.app_context():
            global User
            from lektor.admin.models import User

        app.config['SQLALCHEMY_DATABASE_URI'] = project.database_uri
        app.config['SECRET_KEY'] = project.secret_key

        @app.before_request
        def require_authorization():
            if not (current_user.is_authenticated or
                    request.endpoint in ['users.login', 'users.set_password']):
                return login_manager.unauthorized()

        login_manager = login.LoginManager()
        login_manager.init_app(app)

        @login_manager.user_loader
        def load_user(user_id):
            return User.get(id=user_id)

        class LoginForm(Form):
            username = StringField('username')
            password = PasswordField('password')
            submit = SubmitField('login')

            def validate(self):
                user = User.get(username=self.username.data)
                return user and user.check_password(self.password.data)

        # Public views.
        @bp.route('/login', methods=['GET', 'POST'])
        def login():
            form = LoginForm()
            if form.validate_on_submit():
                logged_in = login_user(User.get(username=form.username.data))
                return (redirect(g.admin_context.admin_root)
                        if logged_in else redirect(url_for('users.login')))
            else:
                logout_user()
            return flask.render_template(
                'login.html', form=form, title='Log In')

        @bp.route('/set_password/<tmp_token>', methods=['GET', 'POST'])
        def set_password(tmp_token):
            user = User.get(tmp_token=tmp_token)

            if not user or user.pw_hash:
                return current_app.login_manager.unauthorized()

            form = LoginForm(username=user.username)
            if form.is_submitted() and form.username.data == user.username:
                user.set_password(form.password.data)
                user.save()
                return redirect(url_for('users.login'))
            return flask.render_template(
                'login.html', form=form, title='Set Password')

        # User views.
        @bp.route('/logout')
        def logout():
            logout_user()
            return redirect(url_for('users.login'))

        @bp.route('/is-admin')
        def is_admin():
            return flask.jsonify(is_admin=_is_admin())

        # Admin views.
        @bp.route('/')
        @admin_required
        def users():
            users = [user.username for user in User.query.all()]
            return flask.jsonify(users=users)

        @bp.route('/add', methods=['POST'])
        @admin_required
        def add_user():
            username = request.get_json()['username']

            user = User(username)
            tmp_token = user.make_tmp_token()
            user.save()

            return flask.jsonify(link=set_password_link(tmp_token))

        @bp.route('/delete', methods=['POST'])
        @admin_required
        def delete_user():
            username = request.get_json()['username']

            user = User.get(username=username)
            if user.id != 1:
                user.delete()
            return ''

        @bp.route('/reset', methods=['POST'])
        @admin_required
        def reset_user():
            username = request.get_json()['username']

            user = User.get(username=username)
            user.unset_password()
            tmp_token = user.make_tmp_token()
            user.save()
            return flask.jsonify(link=set_password_link(tmp_token))
