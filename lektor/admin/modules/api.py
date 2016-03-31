import os
import posixpath

import click
from flask import Blueprint, jsonify, request, g, current_app

from lektor._compat import iteritems, itervalues
from lektor.utils import is_valid_id
from lektor.admin.utils import eventstream
from lektor.publisher import publish, PublishError
from lektor.environment import PRIMARY_ALT


bp = Blueprint('api', __name__, url_prefix='/admin/api')


def get_record_and_parent(path):
    pad = g.admin_context.pad
    record = pad.get(path)
    if record is None:
        parent = pad.get(posixpath.dirname(path))
    else:
        parent = record.parent
    return record, parent


@bp.route('/pathinfo')
def get_path_info():
    """Returns the path segment information for a record."""
    tree_item = g.admin_context.tree.get(request.args['path'])
    segments = []

    while tree_item is not None:
        segments.append({
            'id': tree_item.id,
            'path': tree_item.path,
            'label_i18n': tree_item.label_i18n,
            'exists': tree_item.exists,
            'can_have_children': tree_item.can_have_children
        })
        tree_item = tree_item.get_parent()

    segments.reverse()
    return jsonify(segments=segments)


@bp.route('/recordinfo')
def get_record_info():
    db = g.admin_context.pad.db
    tree_item = g.admin_context.tree.get(request.args['path'])
    children = []
    attachments = []
    alts = []

    for child in tree_item.iter_children():
        if child.is_attachment:
            attachments.append(child)
        else:
            children.append(child)

    primary_alt = db.config.primary_alternative
    if primary_alt is not None:
        for alt in itervalues(tree_item.alts):
            alt_cfg = db.config.get_alternative(alt.id)
            alts.append({
                'alt': alt.id,
                'is_primary': alt.id == PRIMARY_ALT,
                'primary_overlay': alt.id == primary_alt,
                'name_i18n': alt_cfg['name'],
                'exists': alt.exists,
            })

    return jsonify(
        id=tree_item.id,
        path=tree_item.path,
        label_i18n=tree_item.label_i18n,
        exists=tree_item.exists,
        is_attachment=tree_item.is_attachment,
        attachments=[{
            'id': x.id,
            'path': x.path,
            'type': x.attachment_type,
        } for x in attachments],
        children=[{
            'id': x.id,
            'path': x.path,
            'label': x.id,
            'label_i18n': x.label_i18n,
            'visible': x.is_visible,
        } for x in children],
        alts=alts,
        can_have_children=tree_item.can_have_children,
        can_have_attachments=tree_item.can_have_attachments,
        can_be_deleted=tree_item.can_be_deleted,
    )


@bp.route('/previewinfo')
def get_preview_info():
    alt = request.args.get('alt') or PRIMARY_ALT
    record = g.admin_context.pad.get(request.args['path'], alt=alt)
    if record is None:
        return jsonify(exists=False, url=None, is_hidden=True)
    return jsonify(
        exists=True,
        url=record.url_path,
        is_hidden=record.is_hidden
    )


@bp.route('/find', methods=['POST'])
def find():
    alt = request.values.get('alt') or PRIMARY_ALT
    lang = request.values.get('lang') or g.admin_context.info.ui_lang
    q = request.values.get('q')
    builder = current_app.lektor_info.get_builder()
    return jsonify(
        results=builder.find_files(q, alt=alt, lang=lang)
    )


@bp.route('/browsefs', methods=['POST'])
def browsefs():
    alt = request.values.get('alt') or PRIMARY_ALT
    record = g.admin_context.pad.get(request.values['path'], alt=alt)
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


@bp.route('/matchurl')
def match_url():
    record = g.admin_context.pad.resolve_url_path(
        request.args['url_path'], alt_fallback=False)
    if record is None:
        return jsonify(exists=False, path=None, alt=None)
    return jsonify(exists=True, path=record['_path'], alt=record['_alt'])


@bp.route('/rawrecord')
def get_raw_record():
    alt = request.args.get('alt') or PRIMARY_ALT
    ts = g.admin_context.tree.edit(request.args['path'], alt=alt)
    return jsonify(ts.to_json())


@bp.route('/newrecord')
def get_new_record_info():
    # XXX: convert to tree usage
    pad = g.admin_context.pad
    alt = request.args.get('alt') or PRIMARY_ALT
    ts = g.admin_context.tree.edit(request.args['path'], alt=alt)
    if ts.is_attachment:
        can_have_children = False
    elif ts.datamodel.child_config.replaced_with is not None:
        can_have_children = False
    else:
        can_have_children = True
    implied = ts.datamodel.child_config.model

    def describe_model(model):
        primary_field = None
        if model.primary_field is not None:
            f = model.field_map.get(model.primary_field)
            if f is not None:
                primary_field = f.to_json(pad)
        return {
            'id': model.id,
            'name': model.name,
            'name_i18n': model.name_i18n,
            'primary_field': primary_field
        }

    return jsonify({
        'label': ts.record and ts.record.record_label or ts.id,
        'can_have_children': can_have_children,
        'implied_model': implied,
        'available_models': dict(
            (k, describe_model(v)) for k, v in iteritems(pad.db.datamodels)
            if not v.hidden or k == implied)
    })


@bp.route('/newattachment')
def get_new_attachment_info():
    ts = g.admin_context.tree.edit(request.args['path'])
    return jsonify({
        'can_upload': ts.exists and not ts.is_attachment,
        'label': ts.record and ts.record.record_label or ts.id,
    })


@bp.route('/newattachment', methods=['POST'])
def upload_new_attachments():
    alt = request.values.get('alt') or PRIMARY_ALT
    ts = g.admin_context.tree.edit(request.values['path'], alt=alt)
    if not ts.exists or ts.is_attachment:
        return jsonify({
            'bad_upload': True
        })

    buckets = []

    for file in request.files.getlist('file'):
        buckets.append({
            'original_filename': file.filename,
            'stored_filename': ts.add_attachment(file.filename, file),
        })

    return jsonify({
        'bad_upload': False,
        'path': request.form['path'],
        'buckets': buckets,
    })


@bp.route('/newrecord', methods=['POST'])
def add_new_record():
    values = request.get_json()
    alt = values.get('alt') or PRIMARY_ALT
    exists = False

    if not is_valid_id(values['id']):
        return jsonify(valid_id=False, exists=False, path=None)

    path = posixpath.join(values['path'], values['id'])

    ts = g.admin_context.tree.edit(path, datamodel=values.get('model'),
                                   alt=alt)
    with ts:
        if ts.exists:
            exists = True
        else:
            ts.update(values.get('data') or {})

    return jsonify({
        'valid_id': True,
        'exists': exists,
        'path': path
    })


@bp.route('/deleterecord', methods=['POST'])
def delete_record():
    alt = request.values.get('alt') or PRIMARY_ALT
    delete_master = request.values.get('delete_master') == '1'
    if request.values['path'] != '/':
        ts = g.admin_context.tree.edit(request.values['path'], alt=alt)
        with ts:
            ts.delete(delete_master=delete_master)
    return jsonify(okay=True)


@bp.route('/rawrecord', methods=['PUT'])
def update_raw_record():
    values = request.get_json()
    data = values['data']
    alt = values.get('alt') or PRIMARY_ALT
    ts = g.admin_context.tree.edit(values['path'], alt=alt)
    with ts:
        ts.update(data)
    return jsonify(path=ts.path)


@bp.route('/servers')
def get_servers():
    db = g.admin_context.pad.db
    config = db.env.load_config()
    servers = config.get_servers(public=True)
    return jsonify(servers=sorted([x.to_json() for x in servers.values()],
                                  key=lambda x: x['name'].lower()))


@bp.route('/build', methods=['POST'])
def trigger_build():
    builder = current_app.lektor_info.get_builder()
    builder.build_all()
    builder.prune()
    return jsonify(okay=True)


@bp.route('/clean', methods=['POST'])
def trigger_clean():
    builder = current_app.lektor_info.get_builder()
    builder.prune(all=True)
    builder.touch_site_config()
    return jsonify(okay=True)


@bp.route('/publish')
def publish_build():
    db = g.admin_context.pad.db
    server = request.values['server']
    config = db.env.load_config()
    server_info = config.get_server(server)
    info = current_app.lektor_info
    @eventstream
    def generator():
        try:
            event_iter = publish(info.env, server_info.target,
                                 info.output_path) or ()
            for event in event_iter:
                yield {'msg': event}
        except PublishError as e:
            yield {'msg': 'Error: %s' % e}
    return generator()


@bp.route('/ping')
def ping():
    return jsonify(
        project_id=current_app.lektor_info.env.project.id,
        okay=True
    )
