from __future__ import annotations

import hashlib
import os
import shutil
import sqlite3
import stat
import sys
import tempfile
from collections import deque
from contextlib import closing
from contextlib import contextmanager
from contextlib import suppress
from dataclasses import dataclass
from itertools import chain
from itertools import islice
from operator import attrgetter
from pathlib import Path
from pathlib import PurePath
from pathlib import PurePosixPath
from typing import Any
from typing import AbstractSet
from typing import Callable
from typing import Generator
from typing import IO
from typing import Iterable
from typing import Iterator
from typing import NamedTuple
from typing import NewType
from typing import TYPE_CHECKING
from typing import TypeVar

import click

from lektor.build_programs import builtin_build_programs
from lektor.buildfailures import FailureController
from lektor.constants import PRIMARY_ALT
from lektor.context import Context
from lektor.reporter import reporter
from lektor.sourceobj import VirtualSourceObject
from lektor.sourcesearch import find_files
from lektor.utils import process_extra_flags
from lektor.utils import prune_file_and_folder

if TYPE_CHECKING:
    from _typeshed import StrPath
    from lektor.db import Pad

_T = TypeVar("_T")

# SourcePath is the normalized path to a source file.
# - It is always a relative path to a file below Environment.root_path
# - It always uses POSIX path separators (/), even on Windows
SourcePath = NewType("SourcePath", str)


# VirtualSourcePath is the normalized DB-path to a VirtualSourceObject
# - It always starts with a '/'
# - It always includes a single '@' that separates the path to it's parent record
#   from the virtual path part.
VirtualSourcePath = NewType("VirtualSourcePath", str)

# PackedVirtualSourcePathAndAlt is a string that contains both a VirtualSourcePath and
# possible an `alt` for the VirtualSourceObject.  The `alt` and a `@` are prepended to
# the VirtualSourcePath to form the PackedVirtualSourcePathAndAlt.  If `alt` is `None`,
# or if alts are not enabled in the current project, nothing is appended — in that case,
# the PackedVirtualSourcePathAndAlt is the same as the VirtualSourcePath.
#
# - It always contains either one or two '@'s
#
PackedVirtualSourcePathAndAlt = NewType("PackedVirtualSourcePathAndAlt", str)


def create_tables(con):
    can_disable_rowid = (3, 8, 2) <= sqlite3.sqlite_version_info
    if can_disable_rowid:
        without_rowid = "without rowid"
    else:
        without_rowid = ""

    try:
        con.execute(
            f"""
            create table if not exists artifacts (
                artifact text,
                source text,
                source_mtime integer,
                source_size integer,
                source_checksum text,
                is_dir integer,
                is_primary_source integer,
                primary key (artifact, source)
            ) {without_rowid};
        """
        )
        con.execute(
            """
            create index if not exists artifacts_source on artifacts (
                source
            );
        """
        )
        con.execute(
            f"""
            create table if not exists artifact_config_hashes (
                artifact text,
                config_hash text,
                primary key (artifact)
            ) {without_rowid};
        """
        )
        con.execute(
            f"""
            create table if not exists dirty_sources (
                source text,
                primary key (source)
            ) {without_rowid};
        """
        )
        con.execute(
            f"""
            create table if not exists source_info (
                path text,
                alt text,
                lang text,
                type text,
                source text,
                title text,
                primary key (path, alt, lang)
            ) {without_rowid};
        """
        )
    finally:
        con.close()


SQLITE_MAX_VARIABLE_NUMBER = 999  # Default SQLITE_MAX_VARIABLE_NUMBER.


def _batched_for_sql(
    data: Iterable[_T], batch_size: int = SQLITE_MAX_VARIABLE_NUMBER
) -> Generator[tuple[str, list[_T]], None, None]:
    """Return an iterable of (placeholders, chunk) pairs suitable for forming SQL queries.

    The number of question marks in placeholders will match the length of chunk.
    """
    it = iter(data)
    batch = list(islice(it, batch_size))
    while batch:
        placeholders = ",".join(["?"] * len(batch))
        yield placeholders, batch
        batch = list(islice(it, batch_size))


class BuildState:
    def __init__(self, builder, path_cache):
        self.builder = builder

        self.updated_artifacts = []
        self.failed_artifacts = []
        self.path_cache = path_cache

    @property
    def pad(self):
        """The pad for this buildstate."""
        return self.builder.pad

    @property
    def env(self):
        """The environment backing this buildstate."""
        return self.builder.env

    @property
    def config(self):
        """The config for this buildstate."""
        return self.builder.pad.db.config

    def notify_failure(self, artifact, exc_info):
        """Notify about a failure.  This marks a failed artifact and stores
        a failure.
        """
        self.failed_artifacts.append(artifact)
        self.builder.failure_controller.store_failure(artifact.artifact_name, exc_info)
        reporter.report_failure(artifact, exc_info)

    def get_file_info(self, filename):
        if filename:
            return self.path_cache.get_file_info(filename)
        return None

    def to_source_filename(self, filename):
        return self.path_cache.to_source_filename(filename)

    # FIXME: unused? broken
    def get_virtual_source_info(self, virtual_source_path, alt=None):
        virtual_source = self.pad.get(virtual_source_path, alt=alt)
        if virtual_source is not None:
            mtime = virtual_source.get_mtime(self.path_cache)
            checksum = virtual_source.get_checksum(self.path_cache)
        else:
            mtime = checksum = None
        return VirtualSourceInfo(virtual_source_path, alt, mtime, checksum)

    # FIXME: deprecated
    def connect_to_database(self):
        """Returns a database connection for the build state db."""
        return self.builder.connect_to_database()

    def db_connection(self):
        """Context manager to manage a database connection.

        When the context exits normally, the connection is committed then closed.
        If the context exits via exception, the connection is rolled back then closed.
        """
        return self.builder.db_connection()

    def get_destination_filename(self, artifact_name):
        """Returns the destination filename for an artifact name."""
        return os.path.join(
            self.builder.destination_path,
            artifact_name.strip("/").replace("/", os.path.sep),
        )

    def artifact_name_from_destination_filename(self, filename):
        """Returns the artifact name for a destination filename."""
        dst = self.builder.destination_path
        filename = os.path.join(dst, filename)
        if filename.startswith(dst):
            filename = filename[len(dst) :].lstrip(os.path.sep)
            if os.path.altsep:
                filename = filename.lstrip(os.path.altsep)
        return filename.replace(os.path.sep, "/")

    def new_artifact(
        self, artifact_name, sources=None, source_obj=None, extra=None, config_hash=None
    ):
        """Creates a new artifact and returns it."""
        # FIXME: sources should be required?  (Without sources, artification will be
        # pruned.)
        dst_filename = self.get_destination_filename(artifact_name)
        key = self.artifact_name_from_destination_filename(dst_filename)
        return Artifact(
            self,
            key,
            dst_filename,
            sources,
            source_obj=source_obj,
            extra=extra,
            config_hash=config_hash,
        )

    def artifact_exists(self, artifact_name):
        """Given an artifact name this checks if it was already produced."""
        dst_filename = self.get_destination_filename(artifact_name)
        return os.path.exists(dst_filename)

    # FIXME: unused?
    def get_artifact_dependency_infos(self, artifact_name, sources):
        with self.db_connection() as con, closing(con.cursor()) as cur:
            return list(
                self._iter_artifact_dependency_infos(cur, artifact_name, sources)
            )

    # FIXME: unused? (needs tests)
    def _iter_artifact_dependency_infos(self, cur, artifact_name, sources):
        """This iterates over all dependencies as file info objects."""
        root_path = Path(self.env.root_path).resolve()
        path_cache = self.path_cache
        cur.execute(
            """
            select source, source_mtime, source_size, source_checksum, is_dir
            from artifacts
            where artifact = ?
            """,
            [artifact_name],
        )
        found: list[SourcePath] = []
        for info in iter(cur.fetchone, None):  # type: _SourceState
            source_path = info[0]
            source_info: VirtualSourceInfo | FileInfo
            if "@" in source_path:
                source_info = VirtualSourceInfo(*info)
            else:
                source_info = FileInfo(*info)
                source_info.filename = os.path.join(root_path, source_path)
                found.append(source_path)  # type: ignore[arg-type]
            yield source_path, source_info

        # In any case we also iterate over our direct sources, even if the
        # build state does not know about them yet.  This can be caused by
        # an initial build or a change in original configuration.
        source_paths = set(map(path_cache.to_source_filename, sources))
        for source_path in source_paths.difference(found):
            yield source_path, None

    def write_source_info(self, info):
        """Writes the source info into the database.  The source info is
        an instance of :class:`lektor.build_programs.SourceInfo`.
        """
        reporter.report_write_source_info(info)
        source = self.to_source_filename(info.filename)
        with self.db_connection() as con:
            cur = con.cursor()
            for lang, title in info.title_i18n.items():
                cur.execute(
                    """
                    insert or replace into source_info
                        (path, alt, lang, type, source, title)
                        values (?, ?, ?, ?, ?, ?)
                """,
                    [info.path, info.alt, lang, info.type, source, title],
                )

    def prune_source_infos(self):
        """Remove all source infos of files that no longer exist."""
        root_path = Path(self.env.root_path)

        def is_missing(source):
            return not root_path.joinpath(source).exists()

        with self.db_connection() as con, closing(con.cursor()) as cur:
            cur.execute("select distinct source from source_info")
            result: Iterable[tuple[SourcePath]] = iter(cur.fetchone, None)
            to_clean = [source for (source,) in result if is_missing(source)]
            for placeholders, batch in _batched_for_sql(to_clean):
                cur.execute(
                    f"delete from source_info where source in ({placeholders})",
                    batch,
                )
        for source in to_clean:
            reporter.report_prune_source_info(source)

    def remove_artifact(self, artifact_name):
        """Removes an artifact from the build state."""
        # FIXME: should maybe not open a new connection for each removal?
        with self.db_connection() as con, closing(con.cursor()) as cur:
            cur.execute(
                "delete from artifacts where artifact = ?",
                [artifact_name],
            )

    def _any_sources_are_dirty(self, cur, sources):
        """Given a list of sources this checks if any of them are marked
        as dirty.
        """
        sources = [self.to_source_filename(x) for x in sources]
        if not sources:
            return False

        for placeholders, batch in _batched_for_sql(sources):
            cur.execute(
                f"""
                select source from dirty_sources
                where source in ({placeholders}) limit 1
                """,
                batch,
            )
            if cur.fetchone() is not None:
                return True
        return False

    @staticmethod
    def _get_artifact_config_hash(cur, artifact_name):
        """Returns the artifact's config hash."""
        cur.execute(
            """
            select config_hash from artifact_config_hashes
             where artifact = ?
        """,
            [artifact_name],
        )
        rv = cur.fetchone()
        return rv[0] if rv else None

    def check_artifact_is_current(self, artifact_name, sources, config_hash):
        con = self.connect_to_database()
        cur = con.cursor()
        with closing(con):
            # The artifact config changed
            if config_hash != self._get_artifact_config_hash(cur, artifact_name):
                return False

            # If one of our source files is explicitly marked as dirty in the
            # build state, we are not current.
            if self._any_sources_are_dirty(cur, sources):
                return False

            # If we do have an already existing artifact, we need to check if
            # any of the source files we depend on changed.
            cur.execute(
                """
                select source, source_mtime, source_size, source_checksum, is_dir
                from artifacts
                where artifact = ?
                """,
                [artifact_name],
            )
            seen_source_paths = set()
            path_cache = self.path_cache
            for info in iter(cur.fetchone, None):  # type: _SourceState
                if path_cache.is_changed(info):
                    return False
                source_path = info[0]
                if "@" not in source_path:
                    seen_source_paths.add(source_path)

            if not seen_source_paths.issuperset(
                map(path_cache.to_source_filename, sources)
            ):
                return False  # new, unseen source
            return True

    def iter_existing_artifacts(self):
        """Scan output directory for artifacts.

        Returns an iterable of the artifact_names for artifacts found.
        """
        is_ignored = self.env.is_ignored_artifact

        def _unignored(filenames):
            return filter(lambda fn: not is_ignored(fn), filenames)

        dst = self.builder.destination_path
        for dirpath, dirnames, filenames in os.walk(dst):
            dirnames[:] = _unignored(dirnames)
            for filename in _unignored(filenames):
                full_path = os.path.join(dst, dirpath, filename)
                yield self.artifact_name_from_destination_filename(full_path)

    def iter_unreferenced_artifacts(self, all=False):
        """Finds all unreferenced artifacts in the build folder and yields
        them.
        """
        if all:
            yield from self.iter_existing_artifacts()
            return

        def _is_unreferenced(artifact_name):
            # Check whether any of the primary sources for the artifact
            # exist and — if the source can be resolved to a record —
            # correspond to non-hidden records.
            cur.execute(
                """
                SELECT DISTINCT source, path, alt
                FROM artifacts LEFT JOIN source_info USING(source)
                WHERE artifact = ?
                    AND is_primary_source""",
                [artifact_name],
            )
            result: Iterator[tuple[SourcePath, str, str | None]] = iter(cur.fetchone, None)
            for source, path, alt in result:
                if self.get_file_info(source).exists:
                    if path is None:
                        return False  # no record to check
                    record = self.pad.get(path, alt)
                    if record is None:
                        # I'm not sure this should happen, but be safe
                        return False
                    if record.is_visible:
                        return False
            # no sources exist, or those that do belong to hidden records
            return True

        with self.db_connection() as con, closing(con.cursor()) as cur:
            yield from filter(_is_unreferenced, self.iter_existing_artifacts())

    # FIXME: unused? (needs tests)
    def iter_artifacts(self):
        """Iterates over all artifact and their file infos.."""
        with self.db_connection() as con, closing(con.cursor()) as cur:
            cur.execute("select distinct artifact from artifacts order by artifact")
            result: Iterator[tuple[str]] = iter(cur.fetchone, None)
            for (artifact_name,) in result:
                path = self.get_destination_filename(artifact_name)
                info = self.path_cache.get_file_info(path)
                if info.exists:
                    yield artifact_name, info

    def vacuum(self):
        """Vacuums the build db."""
        con = self.connect_to_database()
        with closing(con):
            con.execute("vacuum")


class Artifact:
    """This class represents a build artifact."""

    def __init__(
        self,
        build_state,
        artifact_name,
        dst_filename,
        sources,
        source_obj=None,
        extra=None,
        config_hash=None,
    ):
        self.build_state = build_state
        self.artifact_name = artifact_name
        self.dst_filename = dst_filename
        self.sources = sources
        self.in_update_block = False
        self.updated = False
        self.source_obj = source_obj
        self.extra = extra
        self.config_hash = config_hash

        # Get FileInfos of dependencies as early as possible
        self._source_infos: set[_SourceState] = set(
            map(build_state.get_file_info, sources)
        )

        self._new_artifact_file = None
        self._pending_update_ops = []

    def __repr__(self):
        return "<%s %r>" % (
            self.__class__.__name__,
            self.dst_filename,
        )

    @property
    def is_current(self):
        """Checks if the artifact is current."""
        # If the artifact does not exist, we're not current.
        if not os.path.isfile(self.dst_filename):
            return False

        return self.build_state.check_artifact_is_current(
            self.artifact_name, self.sources, self.config_hash
        )

    # FIXME: unused?
    def UNUSEDget_dependency_infos(self):
        return self.build_state.get_artifact_dependency_infos(
            self.artifact_name, self.sources
        )

    def ensure_dir(self):
        """Creates the directory if it does not exist yet."""
        dst_dir = os.path.dirname(self.dst_filename)
        try:
            os.makedirs(dst_dir)
        except OSError:
            pass

    def open(
        self, mode: str = "rb", encoding: str | None = None, ensure_dir: bool = True
    ) -> IO[Any]:
        """Opens the artifact for reading or writing.  This is transaction
        safe by writing into a temporary file and by moving it over the
        actual source in commit.
        """
        if self._new_artifact_file is not None:
            return open(self._new_artifact_file, mode, encoding=encoding)

        if "r" in mode:
            return open(self.dst_filename, mode, encoding=encoding)

        if ensure_dir:
            self.ensure_dir()
        fd, self._new_artifact_file = tempfile.mkstemp(
            dir=os.path.dirname(self.dst_filename),
            prefix=".__trans",
        )
        return open(fd, mode, encoding=encoding)

    def replace_with_file(self, filename, ensure_dir=True, copy=False):
        """This is similar to open but it will move over a given named
        file.  The file will be deleted by a rollback or renamed by a
        commit.
        """
        if ensure_dir:
            self.ensure_dir()
        if copy:
            with self.open("wb") as df:
                with open(filename, "rb") as sf:
                    shutil.copyfileobj(sf, df)
        else:
            self._new_artifact_file = filename

    def render_template_into(self, template_name, this, **extra):
        """Renders a template into the artifact."""
        rv = self.build_state.env.render_template(
            template_name, self.build_state.pad, this=this, **extra
        )
        with self.open("wb") as f:
            f.write(rv.encode("utf-8") + b"\n")

    def _prune_old_dependencies(self, con: sqlite3.Connection) -> None:
        con.execute(
            "delete from artifacts where artifact = ?", [self.artifact_name]
        ).close()

    def _memorize_dependencies(
        self,
        dependency_infos: AbstractSet[_SourceState],
        con: sqlite3.Connection,
    ) -> None:
        """This updates the dependencies recorded for the artifact based
        on the direct sources plus the provided dependencies.  This also
        stores the config hash.

        This normally defers the operation until commit but the `for_failure`
        more will immediately commit into a new connection.
        """
        rows = [
            (
                self.artifact_name,  # artifact
                *info,  # source, mtime_ns, size, dir_checksum, is_dir
                info in self._source_infos,  # is_primary_source
            )
            for info in self._source_infos.union(dependency_infos)
        ]

        reporter.report_dependencies(rows)

        with closing(con.cursor()) as cur:
            if rows:
                cur.executemany(
                    """
                    insert or replace into artifacts (
                        artifact,
                        source, source_mtime, source_size, source_checksum, is_dir,
                        is_primary_source
                    )
                    values (?, ?, ?, ?, ?, ?, ?)
                    """,
                    rows,
                )

            if self.config_hash is None:
                cur.execute(
                    """
                    delete from artifact_config_hashes
                     where artifact = ?
                    """,
                    [self.artifact_name],
                )
            else:
                cur.execute(
                    """
                    insert or replace into artifact_config_hashes
                           (artifact, config_hash) values (?, ?)
                    """,
                    [self.artifact_name, self.config_hash],
                )

    def clear_dirty_flag(self):
        """Clears the dirty flag for all sources."""
        source_paths = map(attrgetter("source_path"), self._source_infos)

        def operation(con):
            with closing(con.cursor()) as cur:
                for placeholders, batch in _batched_for_sql(source_paths):
                    cur.execute(
                        f"delete from dirty_sources where source in ({placeholders})",
                        batch,
                    )
            reporter.report_dirty_flag(False)

        self._auto_deferred_update_operation(operation)

    def set_dirty_flag(self):
        """Given a list of artifacts this will mark all of their sources
        as dirty so that they will be rebuilt next time.
        """
        source_paths = map(attrgetter("source_path"), self._source_infos)

        def operation(con):
            with closing(con.cursor()) as cur:
                cur.executemany(
                    "insert or replace into dirty_sources (source) values (?)",
                    ((x,) for x in source_paths),
                )
            reporter.report_dirty_flag(True)

        self._auto_deferred_update_operation(operation)

    def _auto_deferred_update_operation(self, f):
        """Helper that defers an update operation when inside an update
        block to a later point.  Otherwise it's auto committed.
        """
        if self.in_update_block:
            self._pending_update_ops.append(f)
            return

        with self.build_state.db_connection() as con:
            f(con)

    @contextmanager
    def update(self):
        """Opens the artifact for modifications.  At the start the dirty
        flag is cleared out and if the commit goes through without errors it
        stays cleared.  The setting of the dirty flag has to be done by the
        caller however based on the `exc_info` on the context.
        """
        build_state = self.build_state
        path_cache = self.build_state.path_cache

        dependency_infos: set[_SourceState] = set()

        def gather_dep(dep: str | VirtualSourceObject) -> None:
            if isinstance(dep, VirtualSourceObject):
                source_info = path_cache.get_virtual_source_info(dep)
            else:
                source_info = build_state.get_file_info(dep)
            dependency_infos.add(source_info)

        if self.in_update_block:
            raise RuntimeError("Artifact is already open for updates.")

        try:
            with Context(self) as ctx, ctx.gather_dependencies(gather_dep):
                self.in_update_block = True
                self.updated = False
                self.clear_dirty_flag()
                try:
                    yield ctx
                finally:
                    self.in_update_block = False
                    self.updated = True

        except BaseException:
            # If an error happened we roll back all changes and record the
            # stacktrace in two locations: we record it on the context so
            # that a called can respond to our failure, and we also persist
            # it so that the dev server can render it out later.
            if self._new_artifact_file is not None:
                with suppress(OSError):
                    os.remove(self._new_artifact_file)
                self._new_artifact_file = None
            self._pending_update_ops = []

            # On error, do not prune old dependencies, just append new ones.
            with self.build_state.db_connection() as con:
                self._memorize_dependencies(dependency_infos, con)

            ctx.exc_info = sys.exc_info()
            self.build_state.notify_failure(self, ctx.exc_info)

        else:
            with self.build_state.db_connection() as con:
                self._prune_old_dependencies(con)
                self._memorize_dependencies(dependency_infos, con)

                for op in self._pending_update_ops:
                    op(con)

                if self._new_artifact_file is not None:
                    os.replace(self._new_artifact_file, self.dst_filename)
                    self._new_artifact_file = None

            self.build_state.updated_artifacts.append(self)
            self.build_state.builder.failure_controller.clear_failure(
                self.artifact_name
            )


class InvalidSourcePath(ValueError):
    """A source path points to a location outside of the project tree."""


class PathCache:
    def __init__(self, pad: Pad):
        self.file_info_cache: dict[Path, FileInfo | NonSourceFileInfo] = {}
        self.virtual_source_info_cache: dict[str, VirtualSourceInfo] = {}
        self.source_filename_cache: dict[str, SourcePath] = {}
        self.pad = pad
        self.root_path = Path(pad.env.root_path).resolve()

    def to_source_filename(self, filename: StrPath) -> SourcePath:
        """Given a path somewhere below the environment this will return the
        short source filename that is used internally.  Unlike the given
        path, this identifier is also platform independent.
        """
        # FIXME: this could be cleaned up (with pathlib?)  FIXME: the cache lifetime of
        # this cache is not right.  It only needs to be invalidated if root_path
        # changes.  The cache could be tied to the Environment or Project; or maybe a
        # global lru_cache could be used...

        key = str(filename)
        cache = self.source_filename_cache
        try:
            return cache[key]
        except KeyError:
            pass
        root_path = self.root_path
        resolved = root_path.joinpath(filename).resolve()
        try:
            relative: PurePath = resolved.relative_to(root_path)
        except ValueError as exc:
            raise InvalidSourcePath(
                f"The path ({filename!s}) is outside of the project tree ({root_path!s})"
            ) from exc
        if not isinstance(relative, PurePosixPath):
            relative = PurePosixPath(relative)
        rv = cache[key] = SourcePath(str(relative))
        return rv

    def get_file_info(self, filename: StrPath) -> FileInfo | NonSourceFileInfo:
        """Returns the file info for a given file.  This will be cached
        on the generator for the lifetime of it.  This means that further
        accesses to this file info will not cause more IO but it might not
        be safe to use the generator after modifications to the original
        files have been performed on the outside.

        Generally this function can be used to acquire the file info for
        any file on the file system but it should onl be used for source
        files or carefully for other things.

        The filename, if given as a relative path is interpreted relative
        to the environment's root_path.

        The filename given can be a source filename.
        """
        resolved = self.root_path.joinpath(filename).resolve()
        source_path: SourcePath | None
        try:
            relative: PurePath = resolved.relative_to(self.root_path)
        except ValueError:
            # Path points outside of the project tree. Use absolute path as key
            source_path = None
        else:
            if not isinstance(relative, PurePosixPath):
                relative = PurePosixPath(relative)
            source_path = SourcePath(str(relative))

        cache = self.file_info_cache
        try:
            return cache[resolved]
        except KeyError:
            state = _get_path_state(resolved, self.pad.env.is_uninteresting_source_name)
            is_dir = state.dir_checksum is not None
            file_info: FileInfo | NonSourceFileInfo
            if source_path is not None:
                file_info = FileInfo(
                    source_path, state.mtime_ns, state.size, state.dir_checksum, is_dir
                )
                file_info.filename = str(resolved)
            else:
                file_info = NonSourceFileInfo(
                    str(resolved),
                    state.mtime_ns,
                    state.size,
                    state.dir_checksum,
                    is_dir,
                )
            return cache.setdefault(resolved, file_info)

    def get_virtual_source_info(
        self, virtual_source: VirtualSourceObject
    ) -> VirtualSourceInfo:
        packed_path = _pack_virtual_source_path(virtual_source.path, virtual_source.alt)
        cache = self.virtual_source_info_cache
        try:
            return cache[packed_path]
        except KeyError:
            mtime = virtual_source.get_mtime(self)
            checksum = virtual_source.get_checksum(self)
            state = VirtualSourceInfo(packed_path, mtime, 0, checksum)
            return cache.setdefault(packed_path, state)

    def _get_source_info(
        self, source_path: SourcePath | PackedVirtualSourcePathAndAlt
    ) -> FileInfo | VirtualSourceInfo:
        if "@" in source_path:
            # FIXME: check cache?
            path, alt = _unpack_virtual_source_path(source_path)  # type: ignore[arg-type]
            virtual_source = self.pad.get(path, alt=alt)
            if virtual_source is None:
                return VirtualSourceInfo(source_path)  # missing
            return self.get_virtual_source_info(virtual_source)

        file_info = self.get_file_info(source_path)
        assert isinstance(file_info, FileInfo)
        return file_info

    def is_changed(self, info: _SourceState) -> bool:
        source_path = info[0]
        current_info = self._get_source_info(source_path)
        assert current_info[0] == source_path
        return current_info != info


class _SourceState(NamedTuple):
    """File metadata used to detect changes."""

    # This is exactly the data that goes in the `artifacts` sqlite table
    source_path: SourcePath | PackedVirtualSourcePathAndAlt
    mtime_ns: int = 0  # zero if missing (b/c)
    size: int | None = None
    dir_checksum: str | None = None
    is_dir: bool = False


class FileInfoMixin:
    filename: str
    mtime_ns: int
    size: int | None
    dir_checksum: str | None
    is_dir: bool

    @property
    def mtime(self) -> int:
        return int(self.mtime_ns / 1000_000_000)

    @property
    def exists(self) -> bool:
        return self.size is not None

    @property
    def checksum(self) -> str:
        if self.is_dir:
            # directories have a checksum that was computed when it was interred in the
            # PathCache
            assert self.dir_checksum is not None
            return self.dir_checksum

        # For regular files, we do not normally keep a checksum, so we need to compute it.
        # This is here solely for b/c.
        # FIXME: deprecate?
        h = hashlib.sha1()
        try:
            with open(self.filename, "rb", buffering=0) as fp:
                chunk = bytearray(16 * 1024)
                while fp.readinto(chunk):
                    h.update(chunk)
        except OSError:
            return "0" * 40  # File is gone (or was never there)?
        return h.hexdigest()

    @property
    def filename_and_checksum(self) -> str:
        """Like 'filename:checksum'."""
        # FIXME: deprecate?
        return f"{self.filename}:{self.checksum}"


class FileInfo(_SourceState, FileInfoMixin):
    source_path: SourcePath
    # resolved (absolute) path
    filename: str


@dataclass(frozen=True)
class NonSourceFileInfo(FileInfoMixin):
    """The "FileInfo" type returned for paths which are outside the project tree."""

    # FIXME: perhaps these should just be deprecated?

    # resolved (absolute) path
    filename: str
    mtime_ns: int = 0
    size: int | None = None
    dir_checksum: str | None = None
    is_dir: bool = False

    @property
    def source(self) -> None:
        return None


class VirtualSourceInfo(_SourceState):
    source_path: PackedVirtualSourcePathAndAlt

    @property
    def path(self):
        return _unpack_virtual_source_path(self.source_path)[0]

    @property
    def alt(self) -> str | None:
        return _unpack_virtual_source_path(self.source_path)[1]

    @property
    def mtime(self) -> int | None:
        if self.mtime_ns is None:
            return None
        return int(self.mtime_ns / 1000_000_000)


class _PathState(NamedTuple):
    size: int | None
    mtime_ns: int
    dir_checksum: str | None


def _get_path_state(
    path: StrPath, is_uninteresting_source_name: Callable[[str], bool]
) -> _PathState:
    # Some failures may be transient, e.g. if a path changed from a directory to a
    # file between the initial stat and the scandir.  Unlikely, yes. But there's no
    # harm in trying twice.
    try:
        return _get_path_state1(path, is_uninteresting_source_name)
    except OSError:
        return _get_path_state1(path, is_uninteresting_source_name)


def _get_path_state1(
    path: StrPath, is_uninteresting_source_name: Callable[[str], bool]
) -> _PathState:
    try:
        st = os.stat(path)
    except FileNotFoundError:
        return _PathState(None, 0, None)

    if not stat.S_ISDIR(st.st_mode):
        return _PathState(st.st_size, st.st_mtime_ns, None)

    def describe_entry(entry: os.DirEntry[str]) -> bytes:
        """A basic description of what a directory entry is."""
        # This is not entirely correct as it does not detect changes for
        # contents from alternatives.  However for the moment it's good
        # enough.
        if entry.is_file():
            return b"\x01"
        if os.path.isfile(os.path.join(path, entry.name, "contents.lr")):
            return b"\x02"
        if entry.is_dir():
            return b"\x03"
        return b"\x00"

    with os.scandir(path) as entries:
        interesting_entries = [
            entry
            for entry in entries
            if not is_uninteresting_source_name(entry.name)
        ]
        dirsize = len(interesting_entries)
        h = hashlib.sha1(b"DIR\0")
        for entry in sorted(interesting_entries, key=attrgetter("name")):
            h.update(entry.name.encode())
            h.update(describe_entry(entry))
            h.update(b"\0")
        return _PathState(dirsize, st.st_mtime_ns, h.hexdigest())


def _pack_virtual_source_path(
    path: VirtualSourcePath, alt: str | None
) -> PackedVirtualSourcePathAndAlt:
    """Pack VirtualSourceObject's path and alt into a single string.

    The full identity key for a VirtualSourceObject is its ``path`` along with its ``alt``.
    (Two VirtualSourceObjects with differing alts are not the same object.)

    This functions packs the (path, alt) pair into a single string for storage
    in the ``artifacts.path`` of the buildstate database.

    Note that if alternatives are not configured for the current site, there is
    only one alt, so we safely omit the alt from the packed path.
    """
    if alt is None or alt == PRIMARY_ALT:
        return path  # type: ignore[return-value]
    return f"{alt}@{path}"  # type: ignore[return-value]


def _unpack_virtual_source_path(
    packed: PackedVirtualSourcePathAndAlt,
) -> tuple[VirtualSourcePath, str | None]:
    """Unpack VirtualSourceObject's path and alt from packed path.

    This is the inverse of _pack_virtual_source_path.
    """
    alt: str | None
    alt, sep, path = packed.partition("@")
    if not sep:
        raise ValueError("A packed virtual source path must include at least one '@'")
    if "@" not in path:
        path, alt = packed, None
    return VirtualSourcePath(path), alt


class Builder:
    def __init__(self, pad, destination_path, buildstate_path=None, extra_flags=None):
        self.extra_flags = process_extra_flags(extra_flags)
        self.pad = pad
        self.destination_path = os.path.abspath(
            os.path.join(pad.db.env.root_path, destination_path)
        )
        if buildstate_path:
            self.meta_path = buildstate_path
        else:
            self.meta_path = os.path.join(self.destination_path, ".lektor")
        self.failure_controller = FailureController(pad, self.destination_path)

        try:
            os.makedirs(self.meta_path)
            if os.listdir(self.destination_path) != [".lektor"]:
                if not click.confirm(
                    click.style(
                        "The build dir %s hasn't been used before, and other "
                        "files or folders already exist there. If you prune "
                        "(which normally follows the build step), "
                        "they will be deleted. Proceed with building?"
                        % self.destination_path,
                        fg="yellow",
                    )
                ):
                    os.rmdir(self.meta_path)
                    raise click.Abort()
        except OSError:
            pass

        create_tables(self.connect_to_database())

    @property
    def env(self):
        """The environment backing this generator."""
        return self.pad.db.env

    @property
    def buildstate_database_filename(self):
        """The filename for the build state database."""
        return os.path.join(self.meta_path, "buildstate")

    def connect_to_database(self):
        con = sqlite3.connect(
            self.buildstate_database_filename,
            isolation_level=None,  # FIXME: why?
            timeout=10,
            check_same_thread=False,  # FIXME: why?
        )
        with con, closing(con.cursor()) as cur:
            cur.execute("pragma journal_mode=WAL")  # FIXME: this is persistent once set
            cur.execute("pragma synchronous=NORMAL")
        return con

    @contextmanager
    def db_connection(self):
        """Context manager to manage a database connection.

        When the context exits normally, the connection is committed then closed.
        If the context exits via exception, the connection is rolled back then closed.
        """
        with closing(self.connect_to_database()) as con:
            with con:
                yield con

    def touch_site_config(self):
        """Touches the site config which typically will trigger a rebuild."""
        project_file = self.env.project.project_file
        try:
            os.utime(project_file)
        except OSError:
            pass

    def find_files(self, query, alt=PRIMARY_ALT, lang=None, limit=50, types=None):
        """Returns a list of files that match the query.  This requires that
        the source info is up to date and is primarily used by the admin to
        show files that exist.
        """
        return find_files(self, query, alt, lang, limit, types)

    def new_build_state(self, path_cache=None):
        """Creates a new build state."""
        if path_cache is None:
            path_cache = PathCache(self.pad)
        return BuildState(self, path_cache)

    def get_build_program(self, source, build_state):
        """Finds the right build function for the given source file."""
        for cls, builder in chain(
            reversed(self.env.build_programs), reversed(builtin_build_programs)
        ):
            if isinstance(source, cls):
                return builder(source, build_state)
        raise RuntimeError("I do not know how to build %r" % source)

    def build_artifact(self, artifact, build_func):
        """Various parts of the system once they have an artifact and a
        function to build it, will invoke this function.  This ultimately
        is what builds.

        The return value is the ctx that was used to build this thing
        if it was built, or `None` otherwise.
        """
        is_current = artifact.is_current
        with reporter.build_artifact(artifact, build_func, is_current):
            if not is_current:
                with artifact.update() as ctx:
                    # Upon builing anything we record a dependency to the
                    # project file.  This is not ideal but for the moment
                    # it will ensure that if the file changes we will
                    # rebuild.
                    project_file = self.env.project.project_file
                    if project_file:
                        ctx.record_dependency(project_file)
                    build_func(artifact)
                return ctx
        return None

    @staticmethod
    def update_source_info(prog, build_state):
        """Updates a single source info based on a program.  This is done
        automatically as part of a build.
        """
        info = prog.describe_source_record()
        if info is not None:
            build_state.write_source_info(info)

    def prune(self, all=False):
        """This cleans up data left in the build folder that does not
        correspond to known artifacts.
        """
        path_cache = PathCache(self.pad)
        build_state = self.new_build_state(path_cache=path_cache)
        with reporter.build(all and "clean" or "prune", self):
            self.env.plugin_controller.emit("before-prune", builder=self, all=all)
            for aft in build_state.iter_unreferenced_artifacts(all=all):
                reporter.report_pruned_artifact(aft)
                filename = build_state.get_destination_filename(aft)
                prune_file_and_folder(filename, self.destination_path)
                build_state.remove_artifact(aft)

            build_state.prune_source_infos()
            if all:
                build_state.vacuum()
            self.env.plugin_controller.emit("after-prune", builder=self, all=all)

    def build(self, source, path_cache=None):
        """Given a source object, builds it."""
        build_state = self.new_build_state(path_cache=path_cache)
        with reporter.process_source(source):
            prog = self.get_build_program(source, build_state)
            self.env.plugin_controller.emit(
                "before-build",
                builder=self,
                build_state=build_state,
                source=source,
                prog=prog,
            )
            prog.build()
            if build_state.updated_artifacts:
                self.update_source_info(prog, build_state)
            self.env.plugin_controller.emit(
                "after-build",
                builder=self,
                build_state=build_state,
                source=source,
                prog=prog,
            )
            return prog, build_state

    def get_initial_build_queue(self):
        """Returns the initial build queue as deque."""
        return deque(self.pad.get_all_roots())

    def extend_build_queue(self, queue, prog):
        queue.extend(prog.iter_child_sources())
        for func in self.env.custom_generators:
            queue.extend(func(prog.source) or ())

    def build_all(self):
        """Builds the entire tree.  Returns the number of failures."""
        failures = 0
        path_cache = PathCache(self.pad)
        # We keep a dummy connection here that does not do anything which
        # helps us with the WAL handling.  See #144
        with self.db_connection(), reporter.build("build", self):
            self.env.plugin_controller.emit("before-build-all", builder=self)
            to_build = self.get_initial_build_queue()
            while to_build:
                source = to_build.popleft()
                prog, build_state = self.build(source, path_cache=path_cache)
                self.extend_build_queue(to_build, prog)
                failures += len(build_state.failed_artifacts)
            self.env.plugin_controller.emit("after-build-all", builder=self)
            if failures:
                reporter.report_build_all_failure(failures)
            return failures

    def update_all_source_infos(self):
        """Fast way to update all source infos without having to build
        everything.
        """
        build_state = self.new_build_state()
        # We keep a dummy connection here that does not do anything which
        # helps us with the WAL handling.  See #144
        with self.db_connection(), reporter.build("source info update", self):
            to_build = self.get_initial_build_queue()
            while to_build:
                source = to_build.popleft()
                with reporter.process_source(source):
                    prog = self.get_build_program(source, build_state)
                    self.update_source_info(prog, build_state)
                self.extend_build_queue(to_build, prog)
            build_state.prune_source_infos()
