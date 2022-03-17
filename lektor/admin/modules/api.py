import os
import posixpath
from dataclasses import dataclass
from dataclasses import field
from functools import wraps
from typing import Any
from typing import Callable
from typing import cast
from typing import Dict
from typing import Iterator
from typing import Mapping
from typing import Optional
from typing import TypeVar

import click
import marshmallow
import marshmallow_dataclass as mdcls
from flask import Blueprint
from flask import current_app
from flask import jsonify
from flask import make_response
from flask import request
from flask import Response

from lektor.admin.context import get_lektor_context
from lektor.admin.context import LektorContext
from lektor.admin.utils import eventstream
from lektor.constants import PRIMARY_ALT
from lektor.datamodel import DataModel
from lektor.db import Record
from lektor.environment.config import ServerInfo
from lektor.publisher import publish
from lektor.publisher import PublishError
from lektor.utils import is_valid_id


bp = Blueprint("api", __name__, url_prefix="/admin/api")


@bp.url_value_preprocessor
def pass_lektor_context(
    endpoint: Optional[str], values: Optional[Dict[str, Any]]
) -> None:
    """Pass LektorContext to each view callable in a `ctx` parameter"""
    assert isinstance(values, dict)
    values["ctx"] = get_lektor_context()


class _ServerInfoField(marshmallow.fields.String):
    def _deserialize(
        self,
        value: str,
        attr: Optional[str],
        data: Optional[Mapping[str, Any]],
        **kwargs: Any
    ) -> ServerInfo:
        lektor_config = self.context["lektor_config"]
        server_id = super()._deserialize(value, attr, data, **kwargs)
        server_info = lektor_config.get_server(server_id)
        if server_info is None:
            raise marshmallow.ValidationError("Invalid server id.")
        return server_info


def _is_valid_alt(value: str) -> bool:
    lektor_config = get_lektor_context().config
    return bool(lektor_config.is_valid_alternative(value))


# Mark types for special validation
_PathType = mdcls.NewType("_PathType", str)
_AltType = mdcls.NewType("_AltType", str, validate=_is_valid_alt)
_BoolType = mdcls.NewType("_BoolType", bool, truthy={1, "1"}, falsy={0, "0"})


class _SchemaBase(marshmallow.Schema):
    TYPE_MAPPING = {ServerInfo: _ServerInfoField}

    class Meta:
        unknown = marshmallow.EXCLUDE


F = TypeVar("F", bound=Callable[..., Any])


def _with_validated(param_type: type) -> Callable[[F], F]:
    """Flask view decorator to validate parameters.

    The validated parameters are placed into the ``validated`` keyword
    arg of the decorated view.

    If the request has a JSON body, the parameters are parsed from that.
    Otherwise, the parameters are parsed from ``request.values``.

    :param param_type: A dataclass which specifies the parameters.
    """
    schema_class = mdcls.class_schema(param_type, base_schema=_SchemaBase)
    schema = schema_class()

    def wrap(f: F) -> F:
        @wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Response:
            if (
                request.method in ("POST", "PUT")
                and request.mimetype == "application/json"
            ):
                data = request.get_json() or {}
            else:
                data = request.values
            schema.context = {
                "lektor_config": kwargs["ctx"].config,
            }
            try:
                kwargs["validated"] = schema.load(data)
            except marshmallow.ValidationError as exc:
                error = {
                    "title": "Invalid parameters",
                    "messages": exc.messages,
                }
                return make_response(jsonify(error=error), 400)
            return f(*args, **kwargs)

        # This cast seems necessary, atm.
        # https://github.com/python/mypy/issues/1927
        return cast(F, wrapper)

    return wrap


@dataclass
class _PathAndAlt:
    path: _PathType
    alt: _AltType = PRIMARY_ALT


@bp.route("/pathinfo")
@_with_validated(_PathAndAlt)
def get_path_info(validated: _PathAndAlt, ctx: LektorContext) -> Response:
    """Returns the path segment information for a record."""
    alt = validated.alt
    tree_item = ctx.tree.get(validated.path)
    segments = []

    while tree_item is not None:
        segments.append(
            {
                "id": tree_item.id,
                "path": tree_item.path,
                "label_i18n": tree_item.get_record_label_i18n(alt),
                "exists": tree_item.exists,
                "can_have_children": tree_item.can_have_children,
            }
        )
        tree_item = tree_item.get_parent()

    segments.reverse()
    return jsonify(segments=segments)


@bp.route("/recordinfo")
@_with_validated(_PathAndAlt)
def get_record_info(validated: _PathAndAlt, ctx: LektorContext) -> Response:
    alt = validated.alt
    tree_item = ctx.tree.get(validated.path)

    return jsonify(
        id=tree_item.id,
        path=tree_item.path,
        label_i18n=tree_item.get_record_label_i18n(alt),
        exists=tree_item.exists,
        is_attachment=tree_item.is_attachment,
        attachments=[
            {
                "id": x.id,
                "path": x.path,
                "type": x.attachment_type,
            }
            for x in tree_item.iter_attachments()
        ],
        children=[
            {
                "id": x.id,
                "path": x.path,
                "label": x.id,
                "label_i18n": x.get_record_label_i18n(alt),
                "visible": x.is_visible,
            }
            for x in tree_item.iter_subpages()
        ],
        alts=[
            {
                "alt": _.id,
                "is_primary": _.id == PRIMARY_ALT,
                "primary_overlay": _.is_primary_overlay,
                "name_i18n": _.name_i18n,
                "exists": _.exists,
            }
            for _ in tree_item.alts.values()
        ],
        can_have_children=tree_item.can_have_children,
        can_have_attachments=tree_item.can_have_attachments,
        can_be_deleted=tree_item.can_be_deleted,
    )


@bp.route("/previewinfo")
@_with_validated(_PathAndAlt)
def get_preview_info(validated: _PathAndAlt, ctx: LektorContext) -> Response:
    record = ctx.pad.get(validated.path, alt=validated.alt)
    if record is None:
        return jsonify(exists=False, url=None, is_hidden=True)
    return jsonify(exists=True, url=record.url_path, is_hidden=record.is_hidden)


@dataclass
class _FindParams:
    q: str
    alt: _AltType = PRIMARY_ALT
    lang: Optional[str] = None


@bp.route("/find", methods=["POST"])
@_with_validated(_FindParams)
def find(validated: _FindParams, ctx: LektorContext) -> Response:
    lang = validated.lang or current_app.config.get("lektor.ui_lang", "en")
    return jsonify(
        results=ctx.builder.find_files(validated.q, alt=validated.alt, lang=lang)
    )


@bp.route("/browsefs", methods=["POST"])
@_with_validated(_PathAndAlt)
def browsefs(validated: _PathAndAlt, ctx: LektorContext) -> Response:
    record = ctx.pad.get(validated.path, alt=validated.alt)
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


@dataclass
class _UrlPath:
    url_path: str


@bp.route("/matchurl")
@_with_validated(_UrlPath)
def match_url(validated: _UrlPath, ctx: LektorContext) -> Response:
    """Find the Record that corresponds to a URL.

    This is used by the admin UI to find the db record that corresponds
    to a page when the preview iframe is navigated.
    """
    record = ctx.pad.resolve_url_path(validated.url_path, alt_fallback=False)
    if not isinstance(record, Record):
        return jsonify(exists=False, path=None, alt=None)
    return jsonify(exists=True, path=record["_path"], alt=record["_alt"])


@bp.route("/rawrecord")
@_with_validated(_PathAndAlt)
def get_raw_record(validated: _PathAndAlt, ctx: LektorContext) -> Response:
    ts = ctx.tree.edit(validated.path, alt=validated.alt)
    return jsonify(ts.to_json())


@bp.route("/newrecord")
@_with_validated(_PathAndAlt)
def get_new_record_info(validated: _PathAndAlt, ctx: LektorContext) -> Response:
    pad = ctx.pad
    alt = validated.alt
    tree_item = ctx.tree.get(validated.path)

    def describe_model(model: DataModel) -> Dict[str, Any]:
        primary_field = None
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

    implied_model = tree_item.implied_child_datamodel
    label_i18n = tree_item.get_record_label_i18n(alt)
    return jsonify(
        {
            "label_i18n": label_i18n,
            "label": label_i18n["en"],
            "can_have_children": tree_item.can_have_children,
            "implied_model": implied_model,
            "available_models": dict(
                (k, describe_model(v))
                for k, v in pad.db.datamodels.items()
                if not v.hidden or k == implied_model
            ),
        }
    )


@bp.route("/newattachment")
@_with_validated(_PathAndAlt)
def get_new_attachment_info(validated: _PathAndAlt, ctx: LektorContext) -> Response:
    tree_item = ctx.tree.get(validated.path)
    label_i18n = tree_item.get_record_label_i18n(validated.alt)
    return jsonify(
        {
            "can_upload": tree_item.can_have_attachments,
            "label_i18n": label_i18n,
            "label": label_i18n["en"],
        }
    )


@bp.route("/newattachment", methods=["POST"])
@_with_validated(_PathAndAlt)
def upload_new_attachments(validated: _PathAndAlt, ctx: LektorContext) -> Response:
    ts = ctx.tree.edit(validated.path, alt=validated.alt)
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
            "path": validated.path,
            "buckets": buckets,
        }
    )


@dataclass
class _NewRecordParams:
    id: str
    model: Optional[str]
    data: Dict[str, Optional[str]]
    path: _PathType
    alt: _AltType = PRIMARY_ALT


@bp.route("/newrecord", methods=["POST"])
@_with_validated(_NewRecordParams)
def add_new_record(validated: _NewRecordParams, ctx: LektorContext) -> Response:
    exists = False

    if not is_valid_id(validated.id):
        return jsonify(valid_id=False, exists=False, path=None)

    path = posixpath.join(validated.path, validated.id)

    ts = ctx.tree.edit(path, datamodel=validated.model, alt=validated.alt)
    with ts:
        if ts.exists:
            exists = True
        else:
            ts.data.update(validated.data)

    return jsonify({"valid_id": True, "exists": exists, "path": path})


@dataclass
class _DeleteRecordParams:
    delete_master: _BoolType
    path: _PathType
    alt: _AltType = PRIMARY_ALT


@bp.route("/deleterecord", methods=["POST"])
@_with_validated(_DeleteRecordParams)
def delete_record(validated: _DeleteRecordParams, ctx: LektorContext) -> Response:
    if validated.path != "/":
        ts = ctx.tree.edit(validated.path, alt=validated.alt)
        with ts:
            ts.delete(delete_master=validated.delete_master)
    return jsonify(okay=True)


@dataclass
class _UpdateRawRecordParams:
    data: Dict[str, Optional[str]]
    path: _PathType
    alt: _AltType = PRIMARY_ALT


@bp.route("/rawrecord", methods=["PUT"])
@_with_validated(_UpdateRawRecordParams)
def update_raw_record(
    validated: _UpdateRawRecordParams, ctx: LektorContext
) -> Response:
    ts = ctx.tree.edit(validated.path, alt=validated.alt)
    with ts:
        ts.data.update(validated.data)
    return jsonify(path=ts.path)


@bp.route("/servers")
def get_servers(ctx: LektorContext) -> Response:
    servers = ctx.config.get_servers(public=True)
    return jsonify(
        servers=sorted(
            [x.to_json() for x in servers.values()], key=lambda x: x["name"].lower()
        )
    )


@bp.route("/build", methods=["POST"])
def trigger_build(ctx: LektorContext) -> Response:
    builder = ctx.builder
    builder.build_all()
    builder.prune()
    return jsonify(okay=True)


@bp.route("/clean", methods=["POST"])
def trigger_clean(ctx: LektorContext) -> Response:
    builder = ctx.builder
    builder.prune(all=True)
    builder.touch_site_config()
    return jsonify(okay=True)


@dataclass
class _PublishBuildParams:
    server_info: ServerInfo = field(metadata=dict(data_key="server"))


@bp.route("/publish")
@_with_validated(_PublishBuildParams)
def publish_build(validated: _PublishBuildParams, ctx: LektorContext) -> Response:
    @eventstream
    def generator() -> Iterator[Dict[str, str]]:
        try:
            event_iter = (
                publish(
                    ctx.env,
                    validated.server_info.target,
                    ctx.output_path,
                    server_info=validated.server_info,
                )
                or ()
            )
            for event in event_iter:
                yield {"msg": event}
        except PublishError as e:
            yield {"msg": "Error: %s" % e}

    return generator()


@bp.route("/ping")
def ping(ctx: LektorContext) -> Response:
    return jsonify(project_id=ctx.project_id, okay=True)
