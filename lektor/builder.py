from __future__ import annotations

import hashlib
import os
import shutil
import sqlite3
import stat
import sys
from collections import deque
from collections import namedtuple
from collections.abc import Sized
from contextlib import contextmanager
from dataclasses import dataclass
from itertools import chain
from typing import Any
from typing import IO

import click

from lektor.build_programs import builtin_build_programs
from lektor.buildfailures import FailureController
from lektor.constants import PRIMARY_ALT
from lektor.context import Context
from lektor.reporter import reporter
from lektor.sourcesearch import find_files
from lektor.utils import create_temp
from lektor.utils import fs_enc
from lektor.utils import process_extra_flags
from lektor.utils import prune_file_and_folder


def create_tables(con):
    can_disable_rowid = (3, 8, 2) <= sqlite3.sqlite_version_info
    if can_disable_rowid:
        without_rowid = "without rowid"
    else:
        without_rowid = ""

    try:
        is_virtual_exists = con.execute(
            """ select count(*) from pragma_table_info('artifacts')
                        where name='is_virtual';
            """
        ).fetchone()[0]
        if not is_virtual_exists:
            con.execute("""drop table if exists artifacts""")
        con.execute(
            f"""
            create table if not exists artifacts (
                artifact text,
                source text,
                source_mtime integer,
                source_size integer,
                source_checksum text,
                is_dir integer,
                is_virtual integer,
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


def _placeholders(values: Sized) -> str:
    """Return SQL '?' placeholders for an array or set of values."""
    return ",".join(["?"] * len(values))


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

    def get_virtual_source_info(self, virtual_source_path, alt=None):
        virtual_source = self.pad.get(virtual_source_path, alt=alt)
        if virtual_source is not None:
            mtime = virtual_source.get_mtime(self.path_cache)
            checksum = virtual_source.get_checksum(self.path_cache)
        else:
            mtime = checksum = None
        return VirtualSourceInfo(virtual_source_path, alt, mtime, checksum)

    def connect_to_database(self):
        """Returns a database connection for the build state db."""
        return self.builder.connect_to_database()

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

    def get_artifact_dependency_infos(self, artifact_name, sources):
        con = self.connect_to_database()
        try:
            cur = con.cursor()
            rv = list(self._iter_artifact_dependency_infos(cur, artifact_name, sources))
        finally:
            con.close()
        return rv

    def _iter_artifact_dependency_infos(self, cur, artifact_name, sources):
        """This iterates over all dependencies as file info objects."""
        cur.execute(
            """
            select source, source_mtime, source_size,
                   source_checksum, is_dir, is_virtual
            from artifacts
            where artifact = ?
        """,
            [artifact_name],
        )
        rv = cur.fetchall()

        found = set()
        for path, mtime, size, checksum, is_dir, is_virtual in rv:
            if is_virtual:
                assert "@" in path
                vpath, alt = _unpack_virtual_source_path(path)
                yield path, VirtualSourceInfo(vpath, alt, mtime, checksum)
            else:
                file_info = FileInfo(
                    self.env, path, mtime, size, checksum, bool(is_dir)
                )
                filename = self.to_source_filename(file_info.filename)
                found.add(filename)
                yield filename, file_info

        # In any case we also iterate over our direct sources, even if the
        # build state does not know about them yet.  This can be caused by
        # an initial build or a change in original configuration.
        for source in sources:
            filename = self.to_source_filename(source)
            if filename not in found:
                yield source, None

    def write_source_info(self, info):
        """Writes the source info into the database.  The source info is
        an instance of :class:`lektor.build_programs.SourceInfo`.
        """
        reporter.report_write_source_info(info)
        source = self.to_source_filename(info.filename)
        con = self.connect_to_database()
        try:
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
            con.commit()
        finally:
            con.close()

    def prune_source_infos(self):
        """Remove all source infos of files that no longer exist."""
        MAX_VARS = 999  # Default SQLITE_MAX_VARIABLE_NUMBER.
        con = self.connect_to_database()
        to_clean = []
        try:
            cur = con.cursor()
            cur.execute(
                """
                select distinct source from source_info
            """
            )
            for (source,) in cur.fetchall():
                fs_path = os.path.join(self.env.root_path, source)
                if not os.path.exists(fs_path):
                    to_clean.append(source)

            if to_clean:
                for i in range(0, len(to_clean), MAX_VARS):
                    chunk = to_clean[i : i + MAX_VARS]
                    cur.execute(
                        f"""
                        delete from source_info
                         where source in ({_placeholders(chunk)})
                        """,
                        chunk,
                    )

                con.commit()
        finally:
            con.close()

        for source in to_clean:
            reporter.report_prune_source_info(source)

    def remove_artifact(self, artifact_name):
        """Removes an artifact from the build state."""
        con = self.connect_to_database()
        try:
            cur = con.cursor()
            cur.execute(
                """
                delete from artifacts where artifact = ?
            """,
                [artifact_name],
            )
            con.commit()
        finally:
            con.close()

    def _any_sources_are_dirty(self, cur, sources):
        """Given a list of sources this checks if any of them are marked
        as dirty.
        """
        sources = [self.to_source_filename(x) for x in sources]
        if not sources:
            return False

        cur.execute(
            f"""
            select source from dirty_sources
            where source in ({_placeholders(sources)})
            limit 1
            """,
            sources,
        )
        return cur.fetchone() is not None

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
        try:
            # The artifact config changed
            if config_hash != self._get_artifact_config_hash(cur, artifact_name):
                return False

            # If one of our source files is explicitly marked as dirty in the
            # build state, we are not current.
            if self._any_sources_are_dirty(cur, sources):
                return False

            # If we do have an already existing artifact, we need to check if
            # any of the source files we depend on changed.
            for _, info in self._iter_artifact_dependency_infos(
                cur, artifact_name, sources
            ):
                # if we get a missing source info it means that we never
                # saw this before.  This means we need to build it.
                if info is None:
                    return False

                if info.is_changed(self):
                    return False

            return True
        finally:
            con.close()

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

        con = self.connect_to_database()
        cur = con.cursor()

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
            for source, path, alt in cur.fetchall():
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

        try:
            yield from filter(_is_unreferenced, self.iter_existing_artifacts())
        finally:
            con.close()

    def iter_artifacts(self):
        """Iterates over all artifact and their file infos.."""
        con = self.connect_to_database()
        try:
            cur = con.cursor()
            cur.execute(
                """
                select distinct artifact from artifacts order by artifact
            """
            )
            rows = cur.fetchall()
            con.close()
            for (artifact_name,) in rows:
                path = self.get_destination_filename(artifact_name)
                info = FileInfo(self.builder.env, path)
                if info.exists:
                    yield artifact_name, info
        finally:
            con.close()

    def vacuum(self):
        """Vacuums the build db."""
        con = self.connect_to_database()
        try:
            con.execute("vacuum")
        finally:
            con.close()


def _describe_fs_path_for_checksum(path):
    """Given a file system path this returns a basic description of what
    this is.  This is used for checksum hashing on directories.
    """
    # This is not entirely correct as it does not detect changes for
    # contents from alternatives.  However for the moment it's good
    # enough.
    if os.path.isfile(path):
        return b"\x01"
    if os.path.isfile(os.path.join(path, "contents.lr")):
        return b"\x02"
    if os.path.isdir(path):
        return b"\x03"
    return b"\x00"


class _ArtifactSourceInfo:
    """Base for classes that contain freshness data about artifact sources.

    Concrete subclasses include FileInfo and VirtualSourceInfo.
    """

    def is_changed(self, build_state: BuildState) -> bool:
        """Determine whether source has changed."""
        raise NotImplementedError()


class FileInfo(_ArtifactSourceInfo):
    """A file info object holds metainformation of a file so that changes
    can be detected easily.
    """

    def __init__(
        self, env, filename, mtime=None, size=None, checksum=None, is_dir=None
    ):
        self.env = env
        self.filename = filename
        if mtime is not None and size is not None and is_dir is not None:
            self._stat = (mtime, size, is_dir)
        else:
            self._stat = None
        self._checksum = checksum

    def _get_stat(self):
        rv = self._stat
        if rv is not None:
            return rv

        try:
            st = os.stat(self.filename)
            mtime = int(st.st_mtime)
            if stat.S_ISDIR(st.st_mode):
                size = len(os.listdir(self.filename))
                is_dir = True
            else:
                size = int(st.st_size)
                is_dir = False
            rv = mtime, size, is_dir
        except OSError:
            rv = 0, -1, False
        self._stat = rv
        return rv

    @property
    def mtime(self):
        """The timestamp of the last modification."""
        return self._get_stat()[0]

    @property
    def size(self):
        """The size of the file in bytes.  If the file is actually a
        dictionary then the size is actually the number of files in it.
        """
        return self._get_stat()[1]

    @property
    def is_dir(self):
        """Is this a directory?"""
        return self._get_stat()[2]

    @property
    def exists(self):
        return self.size >= 0

    @property
    def checksum(self):
        """The checksum of the file or directory."""
        rv = self._checksum
        if rv is not None:
            return rv

        try:
            h = hashlib.sha1()
            if os.path.isdir(self.filename):
                h.update(b"DIR\x00")
                for filename in sorted(os.listdir(self.filename)):
                    if self.env.is_uninteresting_source_name(filename):
                        continue
                    if isinstance(filename, str):
                        filename = filename.encode("utf-8")
                    h.update(filename)
                    h.update(
                        _describe_fs_path_for_checksum(
                            os.path.join(self.filename, filename.decode("utf-8"))
                        )
                    )
                    h.update(b"\x00")
            else:
                with open(self.filename, "rb") as f:
                    while 1:
                        chunk = f.read(16 * 1024)
                        if not chunk:
                            break
                        h.update(chunk)
            checksum = h.hexdigest()
        except OSError:
            checksum = "0" * 40
        self._checksum = checksum
        return checksum

    @property
    def filename_and_checksum(self):
        """Like 'filename:checksum'."""
        return f"{self.filename}:{self.checksum}"

    def unchanged(self, other):
        """Given another file info checks if the are similar enough to
        not consider it changed.
        """
        if not isinstance(other, FileInfo):
            raise TypeError(f"'other' must be a FileInfo, not {other!r}")

        if self.mtime != other.mtime or self.size != other.size:
            return False
        # If mtime and size match, we skip the checksum comparison which
        # might require a file read which we do not want in those cases.
        # (Except if it's a directory, then we won't do that)
        if not self.is_dir:
            return True
        return self.checksum == other.checksum

    def is_changed(self, build_state: BuildState) -> bool:
        other = build_state.get_file_info(self.filename)
        return not self.unchanged(other)


def _pack_virtual_source_path(path, alt):
    """Pack VirtualSourceObject's path and alt into a single string.

    The full identity key for a VirtualSourceObject is its ``path`` along with its
    ``alt``.  (Two VirtualSourceObjects with differing alts are not the same object.)

    This functions packs the (path, alt) pair into a single string for storage
    in the ``artifacts.path`` of the buildstate database.

    Note that if alternatives are not configured for the current site, there is
    only one alt, so we safely omit the alt from the packed path.

    """
    if alt is None or alt == PRIMARY_ALT:
        return path
    return f"{alt}@{path}"


def _unpack_virtual_source_path(packed):
    """Unpack VirtualSourceObject's path and alt from packed path.

    This is the inverse of _pack_virtual_source_path.
    """
    alt, sep, path = packed.partition("@")
    if not sep:
        raise ValueError("A packed virtual source path must include at least one '@'")
    if "@" not in path:
        path, alt = packed, None
    return path, alt


@dataclass
class VirtualSourceInfo(_ArtifactSourceInfo):
    path: str
    alt: str | None
    mtime: int | None = None
    checksum: str | None = None

    def unchanged(self, other):
        if not isinstance(other, VirtualSourceInfo):
            raise TypeError(f"'other' must be a VirtualSourceInfo, not {other!r}")

        if (self.path, self.alt) != (other.path, other.alt):
            raise ValueError(
                "trying to compare mismatched virtual paths: "
                f"{self!r}.unchanged({other!r})"
            )

        return (self.mtime, self.checksum) == (other.mtime, other.checksum)

    def is_changed(self, build_state: BuildState) -> bool:
        other = build_state.get_virtual_source_info(self.path, self.alt)
        return not self.unchanged(other)


artifacts_row = namedtuple(
    "artifacts_row",
    [
        "artifact",
        "source",
        "source_mtime",
        "source_size",
        "source_checksum",
        "is_dir",
        "is_virtual",
        "is_primary_source",
    ],
)


class Artifact:
    """This class represents a build artifact."""

    def __init__(
        self,
        build_state,
        artifact_name,
        dst_filename,
        sources,
        *,
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

        self._new_artifact_file = None
        self._pending_update_ops = []

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.dst_filename!r}>"

    @property
    def is_current(self):
        """Checks if the artifact is current."""
        # If the artifact does not exist, we're not current.
        if not os.path.isfile(self.dst_filename):
            return False

        return self.build_state.check_artifact_is_current(
            self.artifact_name, self.sources, self.config_hash
        )

    def get_dependency_infos(self):
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

        fd, self._new_artifact_file = create_temp(
            prefix=".__trans",
            dir=os.path.dirname(self.dst_filename),
            text="b" not in mode,
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

    def _memorize_dependencies(
        self, dependencies=None, virtual_dependencies=None, for_failure=False
    ):
        """This updates the dependencies recorded for the artifact based
        on the direct sources plus the provided dependencies.  This also
        stores the config hash.

        This normally defers the operation until commit but the `for_failure`
        more will immediately commit into a new connection.
        """

        def operation(con):
            primary_sources = {
                self.build_state.to_source_filename(x) for x in self.sources
            }

            seen = set()
            rows = []
            for source in chain(self.sources, dependencies or ()):
                source = self.build_state.to_source_filename(source)
                if source in seen:
                    continue
                info = self.build_state.get_file_info(source)
                rows.append(
                    artifacts_row(
                        artifact=self.artifact_name,
                        source=source,
                        source_mtime=info.mtime,
                        source_size=info.size,
                        source_checksum=info.checksum,
                        is_dir=info.is_dir,
                        is_virtual=False,
                        is_primary_source=source in primary_sources,
                    )
                )

                seen.add(source)

            for v_source in virtual_dependencies or ():
                checksum = v_source.get_checksum(self.build_state.path_cache)
                mtime = v_source.get_mtime(self.build_state.path_cache)
                rows.append(
                    artifacts_row(
                        artifact=self.artifact_name,
                        source=_pack_virtual_source_path(v_source.path, v_source.alt),
                        source_mtime=mtime,
                        source_size=None,
                        source_checksum=checksum,
                        is_dir=False,
                        is_virtual=True,
                        is_primary_source=False,
                    )
                )

            reporter.report_dependencies(rows)

            cur = con.cursor()
            if not for_failure:
                cur.execute(
                    "delete from artifacts where artifact = ?", [self.artifact_name]
                )
            if rows:
                cur.executemany(
                    """
                    insert or replace into artifacts (
                        artifact, source, source_mtime, source_size,
                        source_checksum, is_dir, is_virtual, is_primary_source)
                    values (?, ?, ?, ?, ?, ?, ?, ?)
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

            cur.close()

        if for_failure:
            con = self.build_state.connect_to_database()
            try:
                operation(con)
            except:  # noqa
                con.rollback()
                con.close()
                raise
            con.commit()
            con.close()
        else:
            self._auto_deferred_update_operation(operation)

    def clear_dirty_flag(self):
        """Clears the dirty flag for all sources."""

        def operation(con):
            sources = [self.build_state.to_source_filename(x) for x in self.sources]
            cur = con.cursor()
            cur.execute(
                f"delete from dirty_sources where source in ({_placeholders(sources)})",
                sources,
            )
            cur.close()
            reporter.report_dirty_flag(False)

        self._auto_deferred_update_operation(operation)

    def set_dirty_flag(self):
        """Given a list of artifacts this will mark all of their sources
        as dirty so that they will be rebuilt next time.
        """

        def operation(con):
            sources = set()
            for source in self.sources:
                sources.add(self.build_state.to_source_filename(source))

            if not sources:
                return

            cur = con.cursor()
            cur.executemany(
                """
                insert or replace into dirty_sources (source) values (?)
            """,
                [(x,) for x in sources],
            )
            cur.close()

            reporter.report_dirty_flag(True)

        self._auto_deferred_update_operation(operation)

    def _auto_deferred_update_operation(self, f):
        """Helper that defers an update operation when inside an update
        block to a later point.  Otherwise it's auto committed.
        """
        if self.in_update_block:
            self._pending_update_ops.append(f)
            return
        con = self.build_state.connect_to_database()
        try:
            f(con)
            con.commit()
        except:  # noqa
            con.rollback()
            raise
        finally:
            con.close()

    @contextmanager
    def update(self):
        """Opens the artifact for modifications.  At the start the dirty
        flag is cleared out and if the commit goes through without errors it
        stays cleared.  The setting of the dirty flag has to be done by the
        caller however based on the `exc_info` on the context.
        """
        ctx = self.begin_update()
        try:
            yield ctx
        except:  # pylint: disable=bare-except  # noqa
            exc_info = sys.exc_info()
            self.finish_update(ctx, exc_info)
        else:
            self.finish_update(ctx)

    def begin_update(self):
        """Begins an update block."""
        if self.in_update_block:
            raise RuntimeError("Artifact is already open for updates.")
        self.updated = False
        ctx = Context(self)
        ctx.push()
        self.in_update_block = True
        self.clear_dirty_flag()
        return ctx

    def _commit(self):
        con = None
        try:
            for op in self._pending_update_ops:
                if con is None:
                    con = self.build_state.connect_to_database()
                op(con)

            if self._new_artifact_file is not None:
                os.replace(self._new_artifact_file, self.dst_filename)
                self._new_artifact_file = None

            if con is not None:
                con.commit()
                con.close()
                con = None

            self.build_state.updated_artifacts.append(self)
            self.build_state.builder.failure_controller.clear_failure(
                self.artifact_name
            )
        finally:
            if con is not None:
                con.rollback()
                con.close()

    def _rollback(self):
        if self._new_artifact_file is not None:
            try:
                os.remove(self._new_artifact_file)
            except OSError:
                pass
            self._new_artifact_file = None
        self._pending_update_ops = []

    def finish_update(self, ctx, exc_info=None):
        """Finalizes an update block."""
        if not self.in_update_block:
            raise RuntimeError("Artifact is not open for updates.")
        ctx.pop()
        self.in_update_block = False
        self.updated = True

        # If there was no error, we memoize the dependencies like normal
        # and then commit our transaction.
        if exc_info is None:
            self._memorize_dependencies(
                ctx.referenced_dependencies,
                ctx.referenced_virtual_dependencies,
            )
            self._commit()
            return

        # If an error happened we roll back all changes and record the
        # stacktrace in two locations: we record it on the context so
        # that a called can respond to our failure, and we also persist
        # it so that the dev server can render it out later.
        self._rollback()

        # This is a special form of dependency memorization where we do
        # not prune old dependencies and we just append new ones and we
        # use a new database connection that immediately commits.
        self._memorize_dependencies(
            ctx.referenced_dependencies,
            ctx.referenced_virtual_dependencies,
            for_failure=True,
        )

        ctx.exc_info = exc_info
        self.build_state.notify_failure(self, exc_info)


class PathCache:
    def __init__(self, env):
        self.file_info_cache = {}
        self.source_filename_cache = {}
        self.env = env

    def to_source_filename(self, filename):
        """Given a path somewhere below the environment this will return the
        short source filename that is used internally.  Unlike the given
        path, this identifier is also platform independent.
        """
        key = filename
        rv = self.source_filename_cache.get(key)
        if rv is not None:
            return rv
        folder = os.path.abspath(self.env.root_path)
        if isinstance(folder, str) and not isinstance(filename, str):
            filename = filename.decode(fs_enc)
        filename = os.path.normpath(os.path.join(folder, filename))
        if filename.startswith(folder):
            filename = filename[len(folder) :].lstrip(os.path.sep)
            if os.path.altsep:
                filename = filename.lstrip(os.path.altsep)
        else:
            raise ValueError(
                f"The given value ({filename!r}) is not below the "
                f"source folder ({self.env.root_path!r})"
            )
        rv = filename.replace(os.path.sep, "/")
        self.source_filename_cache[key] = rv
        return rv

    def get_file_info(self, filename):
        """Returns the file info for a given file.  This will be cached
        on the generator for the lifetime of it.  This means that further
        accesses to this file info will not cause more IO but it might not
        be safe to use the generator after modifications to the original
        files have been performed on the outside.

        Generally this function can be used to acquire the file info for
        any file on the file system but it should onl be used for source
        files or carefully for other things.

        The filename given can be a source filename.
        """
        fn = os.path.join(self.env.root_path, filename)
        rv = self.file_info_cache.get(fn)
        if rv is None:
            self.file_info_cache[fn] = rv = FileInfo(self.env, fn)
        return rv


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
                msg = (
                    f"The build dir {self.destination_path} hasn't been used before, "
                    "and other files or folders already exist there. "
                    "If you prune (which normally follows the build step), "
                    "they will be deleted. Proceed with building?"
                )
                if not click.confirm(click.style(msg, fg="yellow")):
                    os.rmdir(self.meta_path)
                    raise click.Abort()
        except OSError:
            pass

        con = self.connect_to_database()
        try:
            create_tables(con)
        finally:
            con.close()

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
            isolation_level=None,
            timeout=10,
            check_same_thread=False,
        )
        cur = con.cursor()
        cur.execute("pragma journal_mode=WAL")
        cur.execute("pragma synchronous=NORMAL")
        con.commit()
        cur.close()
        return con

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
            path_cache = PathCache(self.env)
        return BuildState(self, path_cache)

    def get_build_program(self, source, build_state):
        """Finds the right build function for the given source file."""
        for cls, builder in chain(
            reversed(self.env.build_programs), reversed(builtin_build_programs)
        ):
            if isinstance(source, cls):
                return builder(source, build_state)
        raise RuntimeError(f"I do not know how to build {source!r}")

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
        path_cache = PathCache(self.env)
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
        path_cache = PathCache(self.env)
        # We keep a dummy connection here that does not do anything which
        # helps us with the WAL handling.  See #144
        con = self.connect_to_database()
        try:
            with reporter.build("build", self):
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
        finally:
            con.close()

    def update_all_source_infos(self):
        """Fast way to update all source infos without having to build
        everything.
        """
        build_state = self.new_build_state()
        # We keep a dummy connection here that does not do anything which
        # helps us with the WAL handling.  See #144
        con = self.connect_to_database()
        try:
            with reporter.build("source info update", self):
                to_build = self.get_initial_build_queue()
                while to_build:
                    source = to_build.popleft()
                    with reporter.process_source(source):
                        prog = self.get_build_program(source, build_state)
                        self.update_source_info(prog, build_state)
                    self.extend_build_queue(to_build, prog)
                build_state.prune_source_infos()
        finally:
            con.close()
