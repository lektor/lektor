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

    child_sources = sorted(list(prog.iter_child_sources()),
                           key=lambda x: x['_id'])
    assert [x['_id'] for x in child_sources] == [
        'blog',
        'extra',
        'hello.txt',
        'projects',
        'test.jpg',
    ]
