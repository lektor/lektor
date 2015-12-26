def get_child_sources(prog):
    return sorted(list(prog.iter_child_sources()), key=lambda x: x['_id'])


def test_basic_build(pad, builder):
    root = pad.root

    prog, build_state = builder.build(root)
    assert prog.source is root
    assert build_state.failed_artifacts == []
    assert build_state.updated_artifacts == prog.artifacts

    artifact, = prog.artifacts
    assert artifact.artifact_name == 'index.html'
    assert artifact.sources == [root.source_filename]
    assert artifact.updated
    assert artifact.extra is None
    assert artifact.config_hash is None


def test_child_sources_basic(pad, builder):
    extra = pad.get('/extra')

    prog, _ = builder.build(extra)
    child_sources = get_child_sources(prog)

    assert [x['_id'] for x in child_sources] == [
        'a',
        'b',
        'hello.txt',
    ]


def test_child_sources_pagination(pad, builder):
    projects = pad.get('/projects')

    prog, _ = builder.build(projects)

    child_sources = get_child_sources(prog)

    assert len(child_sources) == 2
    assert child_sources[0]['_id'] == 'projects'
    assert child_sources[0].page_num == 1
    assert child_sources[1]['_id'] == 'projects'
    assert child_sources[1].page_num == 2

    prog, _ = builder.build(child_sources[0])
    child_sources_p1 = get_child_sources(prog)

    assert [x['_id'] for x in child_sources_p1] == [
        'attachment.txt',
        'bagpipe',
        'coffee',
        'master',
        'oven',
        'secret',
    ]

    prog, _ = builder.build(child_sources[1])
    child_sources_p2 = get_child_sources(prog)

    assert [x['_id'] for x in child_sources_p2] == [
        'postage',
        'slave',
        'wolf',
    ]
