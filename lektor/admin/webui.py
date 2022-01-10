import os
import sys
from typing import NamedTuple
from typing import Optional

from flask import abort
from flask import Flask
from flask import request
from werkzeug.security import safe_join
from werkzeug.utils import append_slash_redirect

from lektor.admin.modules import register_modules
from lektor.builder import Builder
from lektor.buildfailures import FailureController
from lektor.db import Database
from lektor.db import Record
from lektor.reporter import CliReporter


class ResolveResult(NamedTuple):
    artifact_name: Optional[str]
    filename: Optional[str]
    record_path: Optional[str]
    alt: Optional[str]


class LektorInfo:
    def __init__(self, env, output_path, ui_lang="en", extra_flags=None, verbosity=0):
        self.env = env
        self.ui_lang = ui_lang
        self.output_path = output_path
        self.extra_flags = extra_flags
        self.verbosity = verbosity

    def get_pad(self):
        return Database(self.env).new_pad()

    def get_builder(self, pad=None):
        if pad is None:
            pad = self.get_pad()
        return Builder(pad, self.output_path, extra_flags=self.extra_flags)

    def get_failure_controller(self, pad=None):
        if pad is None:
            pad = self.get_pad()
        return FailureController(pad, self.output_path)

    def resolve_artifact(self, url_path, pad=None, redirect_slash=True):
        """Resolves an artifact and also triggers a build if necessary.
        Returns a tuple in the form ``(artifact_name, filename)`` where
        `artifact_name` can be `None` in case a file was targeted explicitly.
        """
        if pad is None:
            pad = self.get_pad()

        artifact_name = filename = record_path = alt = None

        # We start with trying to resolve a source and then use the
        # primary
        source = pad.resolve_url_path(url_path)
        if source is not None:
            # If the request path does not end with a slash but we
            # requested a URL that actually wants a trailing slash, we
            # append it.  This is consistent with what apache and nginx do
            # and it ensures our relative urls work.
            if (
                not url_path.endswith("/")
                and source.url_path != "/"
                and source.url_path != url_path
            ):
                return abort(append_slash_redirect(request.environ))

            with CliReporter(self.env, verbosity=self.verbosity):
                builder = self.get_builder(pad)
                prog, _ = builder.build(source)

            artifact = prog.primary_artifact
            if artifact is not None:
                artifact_name = artifact.artifact_name
                filename = artifact.dst_filename
            alt = source.alt
            if isinstance(source, Record):
                record_path = source.record.path

        if filename is None:
            path_list = url_path.strip("/").split("/")
            if sys.platform == "win32":
                filename = os.path.join(self.output_path, *path_list)
            else:
                filename = safe_join(self.output_path, *path_list)

        return ResolveResult(artifact_name, filename, record_path, alt)


class WebUI(Flask):
    def __init__(
        self,
        env,
        debug=False,
        output_path=None,
        ui_lang="en",
        verbosity=0,
        extra_flags=None,
    ):
        Flask.__init__(self, "lektor.admin", static_url_path="/admin/static")
        self.lektor_info = LektorInfo(
            env, output_path, ui_lang, extra_flags=extra_flags, verbosity=verbosity
        )
        self.debug = debug
        self.config["PROPAGATE_EXCEPTIONS"] = True

        register_modules(self)


WebAdmin = WebUI
