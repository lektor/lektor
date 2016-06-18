import mimetypes
import os
import posixpath
from werkzeug.exceptions import NotFound
from zlib import adler32

from flask import (Blueprint, Response, abort, current_app, render_template,
    request)
from werkzeug.datastructures import Headers
from werkzeug.wsgi import wrap_file

from lektor._compat import BytesIO, string_types


bp = Blueprint('serve', __name__)


def rewrite_html_for_editing(fp, edit_url):
    contents = fp.read()

    button = '''
    <style type="text/css">
      #lektor-edit-link {
        position: fixed;
        z-index: 9999999;
        right: 10px;
        top: 10px;
        position: fixed;
        margin: 0;
        font-family: 'Verdana', sans-serif;
        background: #eee;
        color: #77304c;
        font-weight: normal;
        font-size: 32px;
        padding: 0;
        text-decoration: none!important;
        border: 1px solid #ccc!important;
        width: 40px;
        height: 40px;
        line-height: 40px;
        text-align: center;
        opacity: 0.7;
      }

      #lektor-edit-link:hover {
        background: white!important;
        opacity: 1.0;
        border: 1px solid #aaa!important;
      }
    </style>
    <script type="text/javascript">
      (function() {
        if (window != window.top) {
          return;
        }
        var link = document.createElement('a');
        link.setAttribute('href', '%(edit_url)s?path=' +
            encodeURIComponent(document.location.pathname));
        link.setAttribute('id', 'lektor-edit-link');
        link.innerHTML = '\u270E';
        document.body.appendChild(link);
      })();
    </script>
    ''' % {
        'edit_url': edit_url,
    }

    return BytesIO(contents + button.encode('utf-8'))


def send_file(filename):
    mimetype = mimetypes.guess_type(filename)[0]
    if mimetype is None:
        mimetype = 'application/octet-stream'

    headers = Headers()

    try:
        file = open(filename, 'rb')
        mtime = os.path.getmtime(filename)
        headers['Content-Length'] = os.path.getsize(filename)
    except (IOError, OSError):
        abort(404)

    rewritten = False
    if mimetype == 'text/html':
        rewritten = True
        file = rewrite_html_for_editing(file,
            edit_url=posixpath.join('/', request.script_root, 'admin/edit'))
        del headers['Content-Length']

    headers['Cache-Control'] = 'no-cache, no-store'

    data = wrap_file(request.environ, file)

    rv = Response(data, mimetype=mimetype, headers=headers,
                  direct_passthrough=True)

    if not rewritten:
        # if we know the file modification date, we can store it as
        # the time of the last modification.
        if mtime is not None:
            rv.last_modified = int(mtime)
        rv.cache_control.public = True
        try:
            rv.set_etag('lektor-%s-%s-%s' % (
                os.path.getmtime(filename),
                os.path.getsize(filename),
                adler32(
                    filename.encode('utf-8') if isinstance(filename, string_types)
                    else filename
                ) & 0xffffffff,
            ))
        except OSError:
            pass

    return rv


def handle_build_failure(failure):
    return render_template('build-failure.html', **failure.data)


def serve_up_artifact(path):
    li = current_app.lektor_info
    pad = li.get_pad()

    artifact_name, filename = li.resolve_artifact('/' + path, pad)
    if filename is None:
        abort(404)

    if artifact_name is None:
        artifact_name = path.strip('/')

    # If there was a build failure for the given artifact, we want
    # to render this instead of sending the (most likely missing or
    # corrupted) file.
    ctrl = li.get_failure_controller(pad)
    failure = ctrl.lookup_failure(artifact_name)
    if failure is not None:
        return handle_build_failure(failure)

    return send_file(filename)


@bp.route('/', defaults={'path': ''})
@bp.route('/<path:path>')
def serve_artifact(path):
    return serve_up_artifact(path)


@bp.errorhandler(404)
def serve_error_page(error):
    try:
        return serve_up_artifact('404.html')
    except NotFound as e:
        return e
