from flask import Blueprint, render_template, abort, redirect, request, \
     g, url_for

from lektor.admin.utils import fs_path_to_url_path
from lektor.environment import PRIMARY_ALT
from werkzeug.wsgi import extract_path_info


bp = Blueprint('dash', __name__, url_prefix='/admin')


endpoints = [
    ('/', 'index'),
    ('/publish', 'publish'),
    ('/<path>/edit', 'edit'),
    ('/<path>/delete', 'delete'),
    ('/<path>/preview', 'preview'),
    ('/<path>/add-child', 'add_child'),
    ('/<path>/upload', 'add_attachment'),
]


@bp.route('/edit')
def edit_redirect():
    record = None

    # Find out where we wanted to go to.  We need to chop off the leading
    # /admin on this URL as this is where the admin thinks it's placed.
    path = extract_path_info(request.url_root.rstrip('/').rsplit('/', 1)[0],
                             request.args.get('path', '/'))

    if path is not None:
        record = g.admin_context.pad.resolve_url_path(path, alt_fallback=False)
    if record is None:
        abort(404)
    path = fs_path_to_url_path(record.path.split('@')[0])
    if record.alt != PRIMARY_ALT:
        path += '+' + record.alt
    return redirect(url_for('dash.edit', path=path))


def generic_endpoint(**kwargs):
    """This function is invoked by all dash endpoints."""
    return render_template('dash.html')


for path, endpoint in endpoints:
    bp.add_url_rule(path, endpoint, generic_endpoint)
