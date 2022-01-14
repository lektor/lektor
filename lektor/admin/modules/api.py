import os
import posixpath
from typing import Any
from typing import Dict
from typing import Iterator
from typing import List
from typing import Mapping
from typing import Optional
from typing import Tuple
from typing import Union

import click
from flask import Blueprint
from flask import current_app
from flask import g
from flask import jsonify
from flask import request
from flask import Response

from lektor.admin.utils import eventstream
from lektor.admin.webui import WebUI
from lektor.constants import PRIMARY_ALT
from lektor.datamodel import DataModel
from lektor.db import Record
from lektor.publisher import publish
from lektor.publisher import PublishError
from lektor.utils import is_valid_id


bp = Blueprint("api", __name__, url_prefix="/admin/api")


def get_record_and_parent(path: str) -> Tuple[Optional[Record], Optional[Record]]:
    # XXX: unused?
    pad = g.admin_context.pad
    record = pad.get(path)
    if record is None:
        parent = pad.get(posixpath.dirname(path))
    else:
        parent = record.parent
    return record, parent


@bp.route("/pathinfo")
def get_path_info() -> Response:
    """Returns the path segment information for a record."""
    tree_item = g.admin_context.tree.get(request.args["path"])
    segments = []

    while tree_item is not None:
        segments.append(
            {
                "id": tree_item.id,
                "path": tree_item.path,
                "label_i18n": tree_item.label_i18n,
                "exists": tree_item.exists,
                "can_have_children": tree_item.can_have_children,
            }
        )
        tree_item = tree_item.get_parent()

    segments.reverse()
    return jsonify(segments=segments)


@bp.route("/recordinfo")
def get_record_info() -> Response:
    pad = g.admin_context.pad
    request_path = request.args["path"]
    tree_item = g.admin_context.tree.get(request_path)
    children = []
    attachments = []
    alts = []

    for child in tree_item.iter_children():
        if child.is_attachment:
            attachments.append(child)
        else:
            children.append(child)

    primary_alt = pad.db.config.primary_alternative
    if primary_alt is not None:
        for alt in tree_item.alts.values():
            alt_cfg = pad.db.config.get_alternative(alt.id)
            alts.append(
                {
                    "alt": alt.id,
                    "is_primary": alt.id == PRIMARY_ALT,
                    "primary_overlay": alt.id == primary_alt,
                    "name_i18n": alt_cfg["name"],
                    "exists": alt.exists,
                }
            )

    child_order_by = pad.query(request_path).get_order_by() or []

    def child_sortkey(child: Record) -> List[Any]:
        record = pad.get(child.path)
        assert isinstance(record, Record)
        return record.get_sort_key(child_order_by)

    return jsonify(
        id=tree_item.id,
        path=tree_item.path,
        label_i18n=tree_item.label_i18n,
        exists=tree_item.exists,
        is_attachment=tree_item.is_attachment,
        attachments=[
            {
                "id": x.id,
                "path": x.path,
                "type": x.attachment_type,
            }
            for x in attachments
        ],
        children=[
            {
                "id": x.id,
                "path": x.path,
                "label": x.id,
                "label_i18n": x.label_i18n,
                "visible": x.is_visible,
            }
            for x in sorted(children, key=child_sortkey)
        ],
        alts=alts,
        can_have_children=tree_item.can_have_children,
        can_have_attachments=tree_item.can_have_attachments,
        can_be_deleted=tree_item.can_be_deleted,
    )


@bp.route("/previewinfo")
def get_preview_info() -> Response:
    alt = request.args.get("alt") or PRIMARY_ALT
    record = g.admin_context.pad.get(request.args["path"], alt=alt)
    if record is None:
        return jsonify(exists=False, url=None, is_hidden=True)
    return jsonify(exists=True, url=record.url_path, is_hidden=record.is_hidden)


@bp.route("/find", methods=["POST"])
def find() -> Response:
    assert isinstance(current_app, WebUI)
    alt = request.values.get("alt") or PRIMARY_ALT
    lang = request.values.get("lang") or g.admin_context.info.ui_lang
    q = request.values.get("q")
    builder = current_app.lektor_info.get_builder()
    return jsonify(results=builder.find_files(q, alt=alt, lang=lang))


@bp.route("/browsefs", methods=["POST"])
def browsefs() -> Response:
    alt = request.values.get("alt") or PRIMARY_ALT
    record = g.admin_context.pad.get(request.values["path"], alt=alt)
    okay = False
    if record is not None:
        if record.is_attachment:
            fn = record.attachment_filename
        else:
            fn = record.source_filename
        if os.path.exists(fn):
            click.launch(fn, locate=True)
            okay = True
    return jsonify(okay=okay)


@bp.route("/matchurl")
def match_url() -> Response:
    record = g.admin_context.pad.resolve_url_path(
        request.args["url_path"], alt_fallback=False
    )
    if record is None:
        return jsonify(exists=False, path=None, alt=None)
    return jsonify(exists=True, path=record["_path"], alt=record["_alt"])


@bp.route("/rawrecord")
def get_raw_record() -> Response:
    alt = request.args.get("alt") or PRIMARY_ALT
    ts = g.admin_context.tree.edit(request.args["path"], alt=alt)
    return jsonify(ts.to_json())


@bp.route("/newrecord")
def get_new_record_info() -> Response:
    # XXX: convert to tree usage
    pad = g.admin_context.pad
    alt = request.args.get("alt") or PRIMARY_ALT
    ts = g.admin_context.tree.edit(request.args["path"], alt=alt)
    if ts.is_attachment:
        can_have_children = False
    elif ts.datamodel.child_config.replaced_with is not None:
        can_have_children = False
    else:
        can_have_children = True
    implied = ts.datamodel.child_config.model

    def describe_model(model: DataModel) -> Dict[str, Union[str, Dict[str, str], None]]:
        primary_field: Optional[str] = None
        if model.primary_field is not None:
            f = model.field_map.get(model.primary_field)
            if f is not None:
                primary_field = f.to_json(pad)
        return {
            "id": model.id,
            "name": model.name,
            "name_i18n": model.name_i18n,
            "primary_field": primary_field,
        }

    return jsonify(
        {
            "label": ts.record and ts.record.record_label or ts.id,
            "can_have_children": can_have_children,
            "implied_model": implied,
            "available_models": dict(
                (k, describe_model(v))
                for k, v in pad.db.datamodels.items()
                if not v.hidden or k == implied
            ),
        }
    )


@bp.route("/newattachment")
def get_new_attachment_info() -> Response:
    ts = g.admin_context.tree.edit(request.args["path"])
    return jsonify(
        {
            "can_upload": ts.exists and not ts.is_attachment,
            "label": ts.record and ts.record.record_label or ts.id,
        }
    )


@bp.route("/newattachment", methods=["POST"])
def upload_new_attachments() -> Response:
    alt = request.values.get("alt") or PRIMARY_ALT
    ts = g.admin_context.tree.edit(request.values["path"], alt=alt)
    if not ts.exists or ts.is_attachment:
        return jsonify({"bad_upload": True})

    buckets = []

    for file in request.files.getlist("file"):
        buckets.append(
            {
                "original_filename": file.filename,
                "stored_filename": ts.add_attachment(file.filename, file),
            }
        )

    return jsonify(
        {
            "bad_upload": False,
            "path": request.form["path"],
            "buckets": buckets,
        }
    )


# FIXME: Need better input validation here (on all the POST and PUT views).
# Note that request.get_json() need not even return a dict.  It can return a
# scalar, too.
#
# Perhaps marshmallow_dataclass can help here?
# https://pypi.org/project/marshmallow-dataclass/
#
# For now, punt by adding a bunch of type-narrowing asserts.
#


@bp.route("/newrecord", methods=["POST"])
def add_new_record() -> Response:
    values = request.get_json()
    assert isinstance(values, Mapping)
    assert "alt" not in values or isinstance(values["alt"], str)
    alt = values.get("alt") or PRIMARY_ALT
    exists = False

    assert isinstance(values["id"], str)
    assert isinstance(values["path"], str)

    if not is_valid_id(values["id"]):
        return jsonify(valid_id=False, exists=False, path=None)

    path = posixpath.join(values["path"], values["id"])

    assert "model" not in values or isinstance(values["model"], str)
    assert "data" not in values or isinstance(values["data"], dict)
    ts = g.admin_context.tree.edit(path, datamodel=values.get("model"), alt=alt)
    with ts:
        if ts.exists:
            exists = True
        else:
            ts.update(values.get("data") or {})

    return jsonify({"valid_id": True, "exists": exists, "path": path})


@bp.route("/deleterecord", methods=["POST"])
def delete_record() -> Response:
    alt = request.values.get("alt") or PRIMARY_ALT
    delete_master = request.values.get("delete_master") == "1"
    if request.values["path"] != "/":
        ts = g.admin_context.tree.edit(request.values["path"], alt=alt)
        with ts:
            ts.delete(delete_master=delete_master)
    return jsonify(okay=True)


@bp.route("/rawrecord", methods=["PUT"])
def update_raw_record() -> Response:
    values = request.get_json()
    assert isinstance(values, dict)
    data = values["data"]
    alt = values.get("alt") or PRIMARY_ALT
    ts = g.admin_context.tree.edit(values["path"], alt=alt)
    with ts:
        ts.update(data)
    return jsonify(path=ts.path)


@bp.route("/servers")
def get_servers() -> Response:
    db = g.admin_context.pad.db
    config = db.env.load_config()
    servers = config.get_servers(public=True)

    def orderby(server_json: Dict[str, str]) -> str:
        return server_json["name"].lower()

    return jsonify(servers=sorted([x.to_json() for x in servers.values()], key=orderby))


@bp.route("/build", methods=["POST"])
def trigger_build() -> Response:
    assert isinstance(current_app, WebUI)
    builder = current_app.lektor_info.get_builder()
    builder.build_all()
    builder.prune()
    return jsonify(okay=True)


@bp.route("/clean", methods=["POST"])
def trigger_clean() -> Response:
    assert isinstance(current_app, WebUI)
    builder = current_app.lektor_info.get_builder()
    builder.prune(all=True)
    builder.touch_site_config()
    return jsonify(okay=True)


@bp.route("/publish")
def publish_build() -> Response:
    assert isinstance(current_app, WebUI)
    db = g.admin_context.pad.db
    server = request.values["server"]
    config = db.env.load_config()
    server_info = config.get_server(server)
    info = current_app.lektor_info

    @eventstream
    def generator() -> Iterator[Dict[str, str]]:
        try:
            events = publish(
                info.env,
                server_info.target,
                info.output_path,
                server_info=server_info,
            )
            for event in events:
                yield {"msg": event}
        except PublishError as e:
            yield {"msg": "Error: %s" % e}

    return generator()


@bp.route("/ping")
def ping() -> Response:
    assert isinstance(current_app, WebUI)
    return jsonify(project_id=current_app.lektor_info.env.project.id, okay=True)
