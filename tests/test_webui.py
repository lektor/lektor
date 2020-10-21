import os

import flask
import pytest
from werkzeug.exceptions import HTTPException

from lektor.admin.webui import WebAdmin

app = flask.Flask(__name__)


def test_index_html(tmpdir, env):
    webadmin = WebAdmin(env, output_path=str(tmpdir.mkdir("webadmin")))
    info = webadmin.lektor_info

    def resolve(to_resolve):
        with app.test_request_context(to_resolve):
            return info.resolve_artifact(to_resolve)

    # /dir_with_index_html adds slash, then returns contents of index.html.
    with pytest.raises(HTTPException) as exc:
        resolve("/dir_with_index_html")

    assert exc.value.response.status_code == 301
    assert exc.value.response.headers["Location"] == "dir_with_index_html/"

    artifact_folder = "dir_with_index_html"
    artifact_item = "index.html"
    artifact = "{}/{}".format(artifact_folder, artifact_item)
    artifact_path = os.path.join(
        info.output_path,
        artifact_folder,
        artifact_item,
    )
    assert resolve("/dir_with_index_html/") == (artifact, artifact_path)

    # Same for index.htm as for index.html.
    with pytest.raises(HTTPException) as exc:
        resolve("/dir_with_index_htm")

    assert exc.value.response.status_code == 301
    assert exc.value.response.headers["Location"] == "dir_with_index_htm/"

    artifact_folder = "dir_with_index_htm"
    artifact_item = "index.htm"
    artifact = "{}/{}".format(artifact_folder, artifact_item)
    artifact_path = os.path.join(
        info.output_path,
        artifact_folder,
        artifact_item,
    )
    assert resolve("/dir_with_index_htm/") == (artifact, artifact_path)

    # Empty or absent directory has default resolution behavior.
    artifact_path = os.path.join(info.output_path, "empty")
    assert resolve("/empty") == (None, artifact_path)
    artifact_path = os.path.join(info.output_path, "doesnt_exist")
    assert resolve("/doesnt_exist") == (None, artifact_path)
