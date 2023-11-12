from __future__ import annotations

import logging
import threading
import traceback
import webbrowser
from contextlib import ExitStack
from typing import NamedTuple
from typing import TYPE_CHECKING

from werkzeug.serving import is_running_from_reloader
from werkzeug.serving import run_simple

from lektor.admin import WebAdmin
from lektor.builder import Builder
from lektor.db import Database
from lektor.reporter import CliReporter
from lektor.utils import process_extra_flags
from lektor.watcher import watch_project

if TYPE_CHECKING:
    from _typeshed import StrPath
    from lektor.environment import Environment


class BackgroundBuilder(threading.Thread):
    """Run a thread to watch the project tree and rebuild when changes are noticed.

    This is a contextmanager. On entry, the watcher thread is started, on exit it is
    stopped.

    """

    def __init__(
        self,
        env: Environment,
        output_path: StrPath,
        prune: bool = True,
        verbosity: int = 0,
        extra_flags: dict[str, str] | None = None,
    ):
        threading.Thread.__init__(self)
        self.env = env
        self.output_path = output_path
        self.prune = prune
        self.verbosity = verbosity
        self.extra_flags = extra_flags

        # See https://github.com/samuelcolvin/watchfiles/pull/132
        self.stop_event = threading.Event()

    def __enter__(self) -> BackgroundBuilder:
        self.start()
        return self

    def __exit__(self, *args: object) -> None:
        self.stop_event.set()

    def build(self, update_source_info_first: bool = False) -> None:
        try:
            db = Database(self.env)
            builder = Builder(
                db.new_pad(), self.output_path, extra_flags=self.extra_flags
            )
            if update_source_info_first:
                builder.update_all_source_infos()
            builder.build_all()
            if self.prune:
                builder.prune()
        except Exception:
            traceback.print_exc()

    def run(self) -> None:
        watch = watch_project(self.env, self.output_path, stop_event=self.stop_event)
        with CliReporter(self.env, verbosity=self.verbosity):
            self.build(update_source_info_first=True)
            for _changes in watch:
                self.build()


class BindAddr(NamedTuple):
    host: str
    port: int


def browse_to_address(addr: BindAddr) -> None:
    timer = threading.Timer(1.0, webbrowser.open, (f"http://{addr.host}:{addr.port}",))
    timer.daemon = True
    timer.start()


def run_server(
    bindaddr: BindAddr,
    env: Environment,
    output_path: StrPath,
    prune: bool = True,
    verbosity: int = 0,
    lektor_dev: bool = False,
    ui_lang: str = "en",
    browse: bool = False,
    extra_flags: dict[str, str] | None = None,
) -> None:
    """This runs a server but also spawns a background process.  It's
    not safe to call this more than once per python process!
    """
    bindaddr = BindAddr._make(bindaddr)

    in_main_process = is_running_from_reloader() or not lektor_dev
    extra_flags = process_extra_flags(extra_flags)
    if lektor_dev:
        env.jinja_env.add_extension("jinja2.ext.debug")
    else:
        logging.getLogger("werkzeug").setLevel(logging.WARNING)

    app = WebAdmin(
        env,
        output_path=output_path,
        verbosity=verbosity,
        debug=lektor_dev,
        ui_lang=ui_lang,
        extra_flags=extra_flags,
    )

    if browse and not is_running_from_reloader():
        browse_to_address(bindaddr)

    with ExitStack() as stack:
        if in_main_process:
            env.plugin_controller.emit(
                "server-spawn", bindaddr=bindaddr, extra_flags=extra_flags
            )
            stack.callback(env.plugin_controller.emit, "server-stop")

            background_builder = BackgroundBuilder(
                env,
                output_path=output_path,
                prune=prune,
                verbosity=verbosity,
                extra_flags=extra_flags,
            )
            stack.enter_context(background_builder)

        run_simple(
            bindaddr.host,
            bindaddr.port,
            app,
            use_debugger=True,
            threaded=True,
            use_reloader=lektor_dev,
        )
