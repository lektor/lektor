import sqlite3

from lektor._compat import iteritems
from lektor.environment import PRIMARY_ALT


def _iter_parents(path):
    path = path.strip('/')
    if path:
        pieces = path.split('/')
        for x in range(len(pieces)):
            yield '/' + '/'.join(pieces[:x])


def _find_info(infos, alt, lang):
    for info in infos:
        if info['alt'] == alt and info['lang'] == lang:
            return info


def _id_from_path(path):
    try:
        return path.strip('/').split('/')[-1]
    except IndexError:
        return ''


def _mapping_from_cursor(cur):
    rv = {}
    for path, alt, lang, type, title in cur.fetchall():
        rv.setdefault(path, []).append({
            'id': _id_from_path(path),
            'path': path,
            'alt': alt,
            'type': type,
            'lang': lang,
            'title': title,
        })
    return rv


def _find_best_info(infos, alt, lang):
    for _alt, _lang in [(alt, lang), (PRIMARY_ALT, lang),
                        (alt, 'en'), (PRIMARY_ALT, 'en')]:
        rv = _find_info(infos, _alt, _lang)
        if rv is not None:
            return rv


def _build_parent_path(path, mapping, alt, lang):
    rv = []
    for parent in _iter_parents(path):
        info = _find_best_info(mapping.get(parent) or [], alt, lang)
        id = _id_from_path(info['path'])
        if info is None:
            title = id or '(Index)'
        else:
            title = info.get('title')
        rv.append({
            'id': id,
            'path': parent,
            'title': title
        })
    return rv


def _process_search_results(builder, cur, alt, lang, limit):
    mapping = _mapping_from_cursor(cur)
    rv = []

    files_needed = set()

    for path, infos in iteritems(mapping):
        info = _find_best_info(infos, alt, lang)
        if info is None:
            continue

        for parent in _iter_parents(path):
            if parent not in mapping:
                files_needed.add(parent)

        rv.append(info)
        if len(rv) == limit:
            break

    if files_needed:
        cur.execute('''
            select path, alt, lang, type, title
              from source_info
             where path in (%s)
        ''' % ', '.join(['?'] * len(files_needed)), list(files_needed))
        mapping.update(_mapping_from_cursor(cur))

    for info in rv:
        info['parents'] = _build_parent_path(info['path'], mapping, alt, lang)

    return rv


def find_files(builder, query, alt=PRIMARY_ALT, lang=None, limit=50, types=None):
    if types is None:
        types = ['page']
    else:
        types = list(types)
    languages = ['en']
    if lang not in ('en', None):
        languages.append(lang)
    else:
        lang = 'en'
    alts = [PRIMARY_ALT]
    if alt != PRIMARY_ALT:
        alts.append(alt)

    query = query.strip()
    title_like = '%' + query + '%'
    path_like = '/%' + query.rstrip('/') + '%'

    con = sqlite3.connect(builder.buildstate_database_filename, timeout=10)
    try:
        cur = con.cursor()
        cur.execute('''
            select path, alt, lang, type, title
              from source_info
             where (title like ? or path like ?)
               and lang in (%s)
               and alt in (%s)
               and type in (%s)
          order by title
           collate nocase
             limit ?
        ''' % (', '.join(['?'] * len(languages)),
               ', '.join(['?'] * len(alts)),
               ', '.join(['?'] * len(types))),
               [title_like, path_like] + languages + alts + types + [limit * 2])
        return _process_search_results(builder, cur, alt, lang, limit)
    finally:
        con.close()
