import inspect
import os
import re
from datetime import date

import pytest

from lektor.context import Context
from lektor.db import Database
from lektor.db import F
from lektor.db import get_alts
from lektor.db import Image
from lektor.db import Query
from lektor.db import Video
from lektor.filecontents import FileContents
from lektor.metaformat import serialize


def test_root(pad):
    record = pad.root

    assert record is not None
    assert record["title"] == "Welcome"
    assert record["_template"] == "page.html"
    assert record["_alt"] == "en"
    assert record["_slug"] == ""
    assert record["_id"] == ""
    assert record["_path"] == "/"


def test_project_implied_model(pad):
    project = pad.query("/projects").first()
    assert project is not None
    assert project["_model"] == "project"


def test_child_query_visibility_setting(pad):
    projects = pad.get("/projects")
    assert not projects.children._include_hidden

    project_query = pad.query("/projects")
    assert project_query._include_hidden
    assert not project_query._include_undiscoverable


def test_alt_fallback(pad):
    # page that is missing a german tranlation
    wolf_page = pad.get("/projects/wolf", alt="de")

    # Falls back to primary
    assert wolf_page.alt == "de"
    assert wolf_page["_source_alt"] == "_primary"
    assert wolf_page["name"] == "Wolf"

    # If we ask for the alts of that page, we will only get english
    assert get_alts(wolf_page) == ["en"]

    # Unless we include fallbacks in which case we will also see german
    # show up in the list.
    assert get_alts(wolf_page, fallback=True) == ["en", "de"]


def test_alt_parent(pad):
    wolf_page = pad.get("/projects/wolf", alt="de")
    assert wolf_page.alt == "de"
    assert wolf_page.alt == wolf_page.parent.alt


def test_url_matching_with_customized_slug_in_alt(pad):
    en = pad.resolve_url_path("/projects/slave/")
    assert en.alt == "en"
    assert en["_source_alt"] == "_primary"
    assert en.path == "/projects/slave"

    de = pad.resolve_url_path("/de/projects/sklave/")
    assert de.alt == "de"
    assert de["_source_alt"] == "de"
    assert de.path == "/projects/slave"

    assert get_alts(en) == ["en", "de"]


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/extra/container/a",  # child of hidden page explicit marked as non-hidden
        "/extra/container/hello.txt",  # attachment of hidden page
        "/#fragment",  # fragment should be ignored
        "/?query",  # query should be ignored
        "http:/",  # http scheme should be ignored
        "https:/",  # https scheme should be ignored
    ],
)
def test_resolve_url(pad, path):
    assert pad.resolve_url_path(path) is not None


def test_resolve_url_hidden_page(pad):
    assert pad.resolve_url_path("/extra/container") is None
    assert pad.resolve_url_path("/extra/container", include_invisible=True) is not None


def test_resolve_url_asset(pad):
    assert pad.resolve_url_path("/static/demo.css") is not None
    assert pad.resolve_url_path("/static/demo.css", include_assets=False) is None


@pytest.mark.parametrize(
    "path",
    [
        "ftp:///",  # bad scheme
        "//localhost/",  # path should not have a netloc
    ],
)
def test_resolve_url_invalid_path(pad, path):
    assert pad.resolve_url_path(path) is None


def test_basic_alts(pad):
    with Context(pad=pad):
        assert get_alts() == ["en", "de"]


def test_basic_query_syntax(pad):
    projects = pad.get("/projects")

    encumbered = (
        projects.children.filter((F._slug == "master") | (F._slug == "slave"))
        .order_by("_slug")
        .all()
    )

    assert len(encumbered) == 2
    assert [x["name"] for x in encumbered] == ["Master", "Slave"]


def test_basic_query_syntax_template(pad, eval_expr):
    projects = pad.get("/projects")

    encumbered = eval_expr(
        """
        this.children.filter(
            (F._slug == 'master').or(F._slug == 'slave')
        ).order_by('_slug')
    """,
        pad=pad,
        this=projects,
    ).all()

    assert len(encumbered) == 2
    assert [x["name"] for x in encumbered] == ["Master", "Slave"]


def test_is_child_of(pad):
    projects = pad.get("/projects")
    assert projects.is_child_of(projects)
    assert not projects.is_child_of(projects, strict=True)
    child = projects.children.first()
    assert child.is_child_of(projects)
    assert child.is_child_of(projects, strict=True)


def test_undiscoverable_basics(pad):
    projects = pad.query("/projects")
    assert projects.count() == 8
    assert projects.include_undiscoverable(True).count() == 9
    assert pad.get("/projects").children.count() == 8
    assert "secret" not in [x["_id"] for x in pad.get("/projects").children]
    assert not projects._include_undiscoverable
    assert projects._include_hidden

    secret = pad.get("/projects/secret")
    assert secret.is_undiscoverable
    assert secret.url_path == "/projects/secret/"

    q = secret.children
    assert q._include_undiscoverable is False
    assert q._include_hidden is False
    q = q.include_undiscoverable(True)
    assert q._include_undiscoverable is True
    assert q._include_hidden is False

    secret = pad.resolve_url_path("/projects/secret")
    assert secret is not None
    assert secret.path == "/projects/secret"


def test_attachment_api(pad):
    root = pad.root
    root_attachments = [
        "hello.txt",
        "test-progressive.jpg",
        "test-sof-last.jpg",
        "test.jpg",
        "test.mp4",
    ]
    assert root.attachments.count() == len(root_attachments)
    assert sorted(x["_id"] for x in root.attachments) == root_attachments

    txt = root.attachments.get("hello.txt")
    assert txt is not None
    assert txt["_attachment_type"] == "text"
    assert txt.url_path == "/hello.txt"

    img = root.attachments.get("test.jpg")
    assert img is not None
    assert img["_attachment_type"] == "image"
    assert isinstance(img, Image)
    assert img.url_path == "/test.jpg"

    video = root.attachments.get("test.mp4")
    assert video is not None
    assert video["_attachment_type"] == "video"
    assert isinstance(video, Video)
    assert video.url_path == "/test.mp4"


@pytest.mark.parametrize("alt", ["_primary", "en", "de"])
def test_attachment_url_path_with_alt(pad, alt):
    # Attachments do not vary with alt. There is only one copy of each
    # attachment, with URL corresponding to the PRIMARY_ALT, emitted.
    # Check that the .url_path for an attachment points to the correct
    # URL regardless of alt.
    img = pad.get("test.jpg", alt=alt)
    assert img.url_path == "/test.jpg"


def test_query_normalization(pad):
    projects = pad.get("projects")
    assert pad.get("projects") is projects
    assert pad.get("/projects") is projects
    assert pad.get("/projects/.") is projects
    assert pad.get("//projects/.") is projects


def test_distinct(pad):
    posts = pad.query("blog")
    distinct_categories = posts.distinct("category")
    assert isinstance(distinct_categories, set)
    assert distinct_categories == {"My Category"}
    distinct_tags = posts.distinct("tags")
    assert isinstance(distinct_tags, set)
    assert distinct_tags == {"tag1", "tag2", "tag3"}
    distinct_pub_dates = posts.distinct("pub_date")
    assert distinct_pub_dates == {date(2015, 12, 12), date(2015, 12, 13)}
    assert posts.distinct("foo") == set()
    # Post 2 has no summary; check we don't include Undefined in distinct().
    assert posts.distinct("summary") == {"hello"}


def test_root_pagination(scratch_project, scratch_env):
    base = scratch_project.tree
    with open(os.path.join(base, "models", "page.ini"), "w", encoding="utf-8") as f:
        f.write(
            "[model]\n"
            "label = {{ this.title }}\n\n"
            "[children]\n"
            "model = page\n"
            "[pagination]\n"
            "enabled = yes\n"
            "per_page = 1\n"
            "[fields.title]\n"
            "type = string\n"
            "[fields.body]\n"
            "type = markdown\n"
        )

    for name in "a", "b", "c":
        os.mkdir(os.path.join(base, "content", name))
        with open(
            os.path.join(base, "content", name, "contents.lr"), "w", encoding="utf-8"
        ) as f:
            f.write(f"_model: page\n---\ntitle: Page {name}\n---\nbody: Hello World!\n")

    scratch_pad = Database(scratch_env).new_pad()

    root = scratch_pad.root
    assert root.children.count() == 3

    root_1 = scratch_pad.resolve_url_path("/")
    assert root_1.page_num == 1

    root_2 = scratch_pad.resolve_url_path("/page/2/")
    assert root_2.page_num == 2


def test_undefined_order(pad):
    # A missing value should sort after all others.
    blog_post = pad.db.datamodels["blog-post"]

    class TestQuery(Query):
        def _iterate(self):
            for day, pub_date in [
                (3, "2016-01-03"),
                (4, None),  # No pub_date.
                (1, "2016-01-01"),
                (2, "2016-01-02"),
            ]:
                yield pad.instance_from_data(
                    {"_id": str(day), "_path": f"test/{day}", "pub_date": pub_date},
                    datamodel=blog_post,
                )

    ids = [c["_id"] for c in TestQuery("test", pad).order_by("pub_date")]
    assert ["4", "1", "2", "3"] == ids

    ids = [c["_id"] for c in TestQuery("test", pad).order_by("-pub_date")]
    assert ["3", "2", "1", "4"] == ids


def test_hidden_flag(pad):
    # This page is just not hidden at all
    post = pad.get("blog/post1")
    assert not post.is_hidden

    # The root is never hidden itself unless forced
    root = pad.get("/")
    assert not root.is_hidden

    # The container is hidden
    container = pad.get("extra/container")
    assert container.is_hidden

    # But the child of the container is not
    a = pad.get("extra/container/a")
    assert not a.is_hidden
    assert container.children.all() == [a]

    # Attachments are also always visible
    attachment = pad.get("extra/container/hello.txt")
    assert not attachment.is_hidden


def test_default_order_by(scratch_project, scratch_env):
    tree = scratch_project.tree
    with open(os.path.join(tree, "models", "mymodel.ini"), "w", encoding="utf-8") as f:
        f.write(
            "[children]\n"
            "order_by = title\n"
            "[attachments]\n"
            "order_by = attachment_filename\n"
        )
    os.mkdir(os.path.join(tree, "content", "myobj"))
    with open(
        os.path.join(tree, "content", "myobj", "contents.lr"), "w", encoding="utf-8"
    ) as f:
        f.write("_model: mymodel\n---\ntitle: My Test Object\n")

    pad = Database(scratch_env).new_pad()
    myobj = pad.get("/myobj")
    children = myobj.children
    assert list(children.get_order_by()) == ["title"]
    assert list(children.order_by("explicit").get_order_by()) == ["explicit"]
    assert list(myobj.attachments.get_order_by()) == ["attachment_filename"]


def test_offset_without_limit_query(pad):
    projects = pad.get("/projects")

    x = projects.children.offset(1).order_by("_slug").first()

    assert x["name"] == "Coffee"


def test_Pad_get_invalid_path(pad):
    # On windows '<' and/or '>' are invalid in filenames. These were
    # causing an OSError(errno=EINVAL) exception in Database.load_raw_data
    # that was not being caught. This test exercises that.
    assert pad.get("/<foo>") is None


def test_Database_iter_items_invalid_path(env):
    # Check that there is no problem with uncaught
    # OSError(errno=EINVAL) when a path contains non-filename-safe
    # characters in Database.iter_items.
    db = Database(env)
    assert len(list(db.iter_items("/<foo>"))) == 0


def write_files(*path_text_pairs):
    for path, text in path_text_pairs:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(inspect.cleandoc(text), "utf-8")


@pytest.fixture
def dotted_slug_test_records(scratch_project_data):
    content_path = scratch_project_data / "content"
    write_files(
        (
            content_path / "test_dotted/contents.lr",
            """
            title: Test Dotted
            ---
            _slug: subdir/test.dotted
            """,
        ),
        (
            content_path / "test_dotted/child/contents.lr",
            """
            title: Test Dotted Child
            """,
        ),
    )


@pytest.fixture
def primary_alt_is_prefixed(scratch_project_data):
    project_file = scratch_project_data / "Scratch.lektorproject"
    content = project_file.read_text(encoding="utf-8")
    write_files(
        (
            project_file,
            content.replace(
                "[alternatives.en]\n",
                ("[alternatives.en]\nurl_prefix = /en/\n"),
            ),
        )
    )


@pytest.fixture
def paginated_pages(scratch_project_data):
    write_files(
        (
            scratch_project_data / "content/paginated/contents.lr",
            """
            _model: paginated
            ---
            title: Test Paginated
            """,
        ),
        (
            scratch_project_data / "content/paginated.dotted/contents.lr",
            """
            _model: paginated
            ---
            title: Test Paginated with dotted name
            """,
        ),
        (
            scratch_project_data / "models/paginated.ini",
            """
            [model]
            name = Paginated
            extends = page

            [pagination]
            enabled = true
            """,
        ),
    )


@pytest.fixture
def dummy_attachment(scratch_project_data):
    attachment = scratch_project_data / "content/test.txt"
    write_files((attachment, "some text"))


@pytest.mark.parametrize(
    "path, clean_url_path",
    [
        ("/test_dotted", "subdir/test.dotted"),
        ("/test_dotted/child", "subdir/_test.dotted/child"),
    ],
)
@pytest.mark.usefixtures("dotted_slug_test_records")
def test_Record_get_clean_url_path(scratch_pad, path, clean_url_path):
    record = scratch_pad.get(path)
    assert record._get_clean_url_path() == clean_url_path


@pytest.mark.usefixtures("primary_alt_is_prefixed")
def test_Record_get_url_path_defaults_to_primary_alt(scratch_pad):
    record = scratch_pad.get("/")
    assert record._get_url_path() == "/en"


@pytest.mark.parametrize(
    "path, alt, page_num, url_path",
    [
        ("/", "en", None, "/"),
        ("/", "de", None, "/de/"),
        ("/paginated", "en", 1, "/paginated/"),
        ("/paginated", "de", 2, "/de/paginated/page/2/"),
        ("/test_dotted", "en", None, "/subdir/test.dotted"),
        ("/test_dotted", "de", None, "/de/subdir/test.dotted"),
    ],
)
@pytest.mark.usefixtures("dotted_slug_test_records", "paginated_pages")
def test_Page_url_path(scratch_pad, path, alt, page_num, url_path):
    page = scratch_pad.get(path, alt=alt, page_num=page_num)
    assert page.url_path == url_path


@pytest.mark.usefixtures("primary_alt_is_prefixed")
def test_Page_url_path_is_for_primary_alt(scratch_pad):
    page = scratch_pad.get("/")
    assert page.url_path == "/en/"


@pytest.mark.usefixtures("paginated_pages")
def test_Page_url_path_raise_error_if_paginated_and_dotted(scratch_pad):
    page = scratch_pad.get("/paginated.dotted")
    with pytest.raises(Exception) as exc_info:
        _ = page.url_path
    assert re.match(
        r"(?=.*\bextension\b)(?=.*\bpagination\b).*\bcannot be used",
        str(exc_info.value),
    )


@pytest.mark.parametrize("alt", ["en", "de"])
@pytest.mark.usefixtures("primary_alt_is_prefixed", "dummy_attachment")
def test_Attachment_url_path_is_for_primary_alt(scratch_pad, alt):
    attachment = scratch_pad.get("/test.txt")
    assert attachment.url_path == "/en/test.txt"


@pytest.mark.parametrize(
    "path",
    [
        "/",  # Page
        "hello.txt",  # Attachment
    ],
)
def test_Record_contents_is_deprecated(pad, path):
    with pytest.deprecated_call(match=r"contents") as warnings:
        assert isinstance(pad.get(path).contents, FileContents)
    assert all(w.filename == __file__ for w in warnings)


@pytest.mark.parametrize(
    "url, base_url, absolute, external, project_url, expected",
    [
        ("/a/b.html", "/a/", None, None, None, "b.html"),
        ("/a/b/", "/a/", None, None, None, "b/"),
        ("/a/b/", "/a", None, None, None, "a/b/"),
        ("/a/b/", "/a", True, None, None, "/a/b/"),
        ("/a/b/", "/a", True, None, "https://example.net/pfx/", "/pfx/a/b/"),
        ("/a/b/", "/a", None, True, "https://example.org", "https://example.org/a/b/"),
    ],
)
def test_Pad_make_url(url, base_url, absolute, external, project_url, expected, pad):
    if project_url is not None:
        pad.db.config.values["PROJECT"]["url"] = project_url
    assert pad.make_url(url, base_url, absolute, external) == expected


def test_Pad_make_url_raises_runtime_error_if_no_project_url(pad):
    with pytest.raises(RuntimeError, match="(?i)configure the url in the project"):
        pad.make_url("/a/b", external=True)


def test_Pad_make_url_raises_runtime_error_if_no_base_url(pad):
    with pytest.raises(RuntimeError, match="(?i)no base url"):
        pad.make_url("/a/b")


def test_Query_include_hidden_and_undiscoverable(scratch_project_data, scratch_pad):
    def make_child(name, data):
        contents_lr = scratch_project_data / "content" / name / "contents.lr"
        contents_lr.parent.mkdir()
        contents_lr.write_text("".join(serialize(data.items())))

    make_child("hidden", {"_hidden": "yes"})
    make_child("undiscoverable", {"_discoverable": "no"})
    make_child("hidden-undiscoverable", {"_hidden": "yes", "_discoverable": "no"})

    children = scratch_pad.root.children

    def paths(query: Query) -> set:
        return {child.path for child in query}

    assert paths(children) == set()
    assert paths(children.include_hidden(True)) == {"/hidden"}
    assert paths(children.include_undiscoverable(True)) == {"/undiscoverable"}
    assert paths(children.include_hidden(True).include_undiscoverable(True)) == {
        "/hidden",
        "/undiscoverable",
        "/hidden-undiscoverable",
    }
