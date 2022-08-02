from pathlib import Path

import pytest
from markers import imagemagick


def get_child_sources(prog):
    return sorted(list(prog.iter_child_sources()), key=lambda x: x["_id"])


@imagemagick
def test_basic_build(pad, builder):
    root = pad.root

    prog, build_state = builder.build(root)
    assert prog.source is root
    assert build_state.failed_artifacts == []

    (artifact,) = prog.artifacts
    # Root and its thumbnail image were updated.
    assert artifact in build_state.updated_artifacts
    assert artifact.artifact_name == "index.html"
    assert set(artifact.sources) == set(root.iter_source_filenames())
    assert artifact.updated
    assert artifact.extra is None
    assert artifact.config_hash is None


def test_child_sources_basic(pad, builder):
    extra = pad.get("/extra")

    prog, _ = builder.build(extra)
    child_sources = get_child_sources(prog)

    assert [x["_id"] for x in child_sources] == [
        "a",
        "b",
        "container",  # hidden children should be built, too
        "file.ext",
        "hello.txt",
        "paginated",
        "slash-slug",
    ]


def test_child_sources_pagination(pad, builder):
    projects = pad.get("/projects")

    def ids(sources):
        return [x["_id"] for x in sources]

    prog, _ = builder.build(projects)

    child_sources = get_child_sources(prog)
    assert ids(child_sources) == [
        "attachment.txt",
        "filtered",
        "projects",
        "projects",
        "secret",
    ]

    page1 = child_sources[2]
    assert page1["_id"] == "projects"
    assert page1.page_num == 1
    page2 = child_sources[3]
    assert page2["_id"] == "projects"
    assert page2.page_num == 2

    prog, _ = builder.build(page1)
    child_sources_p1 = get_child_sources(prog)

    assert ids(child_sources_p1) == [
        "bagpipe",
        "coffee",
        "master",
        "oven",
    ]

    prog, _ = builder.build(page2)
    child_sources_p2 = get_child_sources(prog)

    assert ids(child_sources_p2) == [
        "postage",
        "slave",
        "wolf",
    ]


def test_basic_artifact_current_test(pad, builder, reporter):
    post1 = pad.get("blog/post1")

    def build():
        reporter.clear()
        prog, _ = builder.build(post1)
        return prog.artifacts[0]

    artifact = build()

    assert reporter.get_major_events() == [
        (
            "enter-source",
            {
                "source": post1,
            },
        ),
        (
            "start-artifact-build",
            {
                "artifact": artifact,
                "is_current": False,
            },
        ),
        (
            "build-func",
            {
                "func": "lektor.build_programs.PageBuildProgram",
            },
        ),
        (
            "finish-artifact-build",
            {
                "artifact": artifact,
            },
        ),
        (
            "leave-source",
            {
                "source": post1,
            },
        ),
    ]

    assert set(reporter.get_recorded_dependencies()) == {
        "Website.lektorproject",
        "content/blog/post1/contents+en.lr",
        "content/blog/post1/contents.lr",
        "content/blog/post1/hello.txt+en.lr",
        "content/blog/post1/hello.txt.lr",
        "templates/blog-post.html",
        "templates/layout.html",
        "models/blog-post.ini",
    }

    assert artifact.is_current

    artifact = build()

    assert artifact.is_current

    assert reporter.get_major_events() == [
        (
            "enter-source",
            {
                "source": post1,
            },
        ),
        (
            "start-artifact-build",
            {
                "artifact": artifact,
                "is_current": True,
            },
        ),
        (
            "build-func",
            {
                "func": "lektor.build_programs.PageBuildProgram",
            },
        ),
        (
            "finish-artifact-build",
            {
                "artifact": artifact,
            },
        ),
        (
            "leave-source",
            {
                "source": post1,
            },
        ),
    ]


def test_basic_template_rendering(pad, builder):
    root = pad.root

    prog, _ = builder.build(root)
    artifact = prog.artifacts[0]

    with artifact.open("rb") as f:
        rv = f.read().decode("utf-8")

    assert artifact.artifact_name == "index.html"

    assert "<title>My Website</title>" in rv
    assert "<h1>Welcome</h1>" in rv
    assert '<link href="static/style.css" rel="stylesheet">' in rv
    assert "<p>Welcome to this pretty nifty website.</p>" in rv


def test_attachment_copying(pad, builder):
    root = pad.root
    text_file = root.attachments.get("hello.txt")

    prog, _ = builder.build(text_file)
    artifact = prog.artifacts[0]

    assert artifact.artifact_name == "hello.txt"

    with artifact.open("rb") as f:
        rv = f.read().decode("utf-8").strip()
        assert rv == "Hello I am an Attachment"


def test_asset_processing(pad, builder):
    static = pad.asset_root.get_child("static")

    prog, _ = builder.build(static)
    assets = list(prog.iter_child_sources())
    assert len(assets) == 1
    assert assets[0].name == "demo.css"

    prog, _ = builder.build(assets[0])
    with prog.artifacts[0].open("rb") as f:
        rv = f.read().decode("utf-8").strip()
        assert "color: red" in rv


def test_included_assets(pad, builder):
    # In demo-project/Website.lektorproject, included_assets = "_*".
    root = pad.asset_root

    prog, _ = builder.build(root)
    assets = list(prog.iter_child_sources())
    assert "_include_me_despite_underscore" in [a.name for a in assets]


def test_excluded_assets(pad, builder):
    # In demo-project/Website.lektorproject, excluded_assets = "foo*".
    root = pad.asset_root

    prog, _ = builder.build(root)
    assets = list(prog.iter_child_sources())
    assert "foo-prefix-makes-me-excluded" not in [a.name for a in assets]


def test_iter_child_pages(child_sources_test_project_builder):
    # Test that child sources are built even if they're filtered out by a
    # pagination query like "this.children.filter(F._model == 'doesnt-exist')".
    builder = child_sources_test_project_builder
    pad = builder.pad
    prog, _ = builder.build(pad.root)
    assert builder.pad.get("filtered-page") in prog.iter_child_sources()


def test_iter_child_attachments(child_sources_test_project_builder):
    # Test that attachments are built, even if a pagination has no items.
    builder = child_sources_test_project_builder
    pad = builder.pad
    prog, _ = builder.build(pad.root)
    assert builder.pad.get("attachment.txt") in prog.iter_child_sources()


@pytest.mark.parametrize(
    "parent_path, child_name",
    [
        ("/extra", "container"),  # a hidden page
        ("/extra/container", "a"),  # a page whose parent is hidden
        ("/extra/container", "hello.txt"),  # an attachment whose parent is hidden
    ],
)
def test_iter_children_of_hidden_pages(builder, pad, parent_path, child_name):
    # Test that child sources are built even if they're parent is hidden
    parent = pad.get(parent_path)
    child = pad.get(f"{parent_path}/{child_name}")
    # sanity checks
    assert parent is not None and child is not None
    assert parent.is_hidden or child.is_hidden

    prog, _ = builder.build(parent)
    assert child in prog.iter_child_sources()


def test_record_is_file(pad, builder):
    record = pad.get("/extra/file.ext")

    prog, _ = builder.build(record)
    (artifact,) = prog.artifacts
    assert artifact.artifact_name == "extra/file.ext"


def test_slug_contains_slash(pad, builder):
    record = pad.get("/extra/slash-slug")

    prog, _ = builder.build(record)
    (artifact,) = prog.artifacts
    assert artifact.artifact_name == "extra/long/path/index.html"


def test_asseturl_dependency_tracking_integration(
    scratch_project_data, scratch_pad, scratch_builder
):
    scratch_project_data.joinpath("templates/page.html").write_text(
        "{{ '/asset.txt'|asseturl }}", "utf-8"
    )
    asset_txt = scratch_project_data / "assets/asset.txt"
    asset_txt.parent.mkdir(exist_ok=True)
    asset_txt.write_text("an asset\n", "utf-8")

    prog, build_state = scratch_builder.build(scratch_pad.root)
    assert len(build_state.updated_artifacts) == 1
    output = Path(prog.artifacts[0].dst_filename)
    asset_url = output.read_text(encoding="utf-8").rstrip()

    prog, build_state = scratch_builder.build(scratch_pad.root)
    assert len(build_state.updated_artifacts) == 0

    asset_txt.write_text("updated asset\n", "utf-8")
    prog, build_state = scratch_builder.build(scratch_pad.root)
    updated_asset_url = output.read_text(encoding="utf-8").rstrip()
    assert updated_asset_url != asset_url
    assert len(build_state.updated_artifacts) == 1


def test_prune_remove_artifacts_of_hidden_pages(scratch_project_data, scratch_builder):
    pad = scratch_builder.pad
    # Build root page
    prog, _ = scratch_builder.build(pad.root)
    (artifact,) = prog.artifacts
    assert Path(artifact.dst_filename).is_file()

    # Do a prune.  Output artifact should survive
    pad.cache.flush()
    scratch_builder.prune()
    assert Path(artifact.dst_filename).is_file()

    # Mark page as hidden, prune should then clean the artifact
    contents_lr = scratch_project_data.joinpath("content/contents.lr")
    contents_lr.write_text(contents_lr.read_text() + "\n---\n_hidden: yes\n")
    pad.cache.flush()
    scratch_builder.prune()
    assert not Path(artifact.dst_filename).is_file()
