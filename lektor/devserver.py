import os
import threading
import time
import traceback

from werkzeug.serving import run_simple
from werkzeug.serving import WSGIRequestHandler

from lektor.admin import WebAdmin
from lektor.builder import Builder
from lektor.db import Database
from lektor.reporter import CliReporter
from lektor.utils import portable_popen
from lektor.utils import process_extra_flags
from lektor.watcher import Watcher


class SilentWSGIRequestHandler(WSGIRequestHandler):
    def log(self, type, message, *args):
        pass


class BackgroundBuilder(threading.Thread):
    def __init__(self, env, output_path, prune=True, verbosity=0, extra_flags=None):
        threading.Thread.__init__(self)
        self.env = env
        self.output_path = output_path
        self.prune = prune
        self.verbosity = verbosity
        self.last_build = time.time()
        self.extra_flags = extra_flags

    def build(self, update_source_info_first=False):
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
        else:
            self.last_build = time.time()

    def run(self):
        with CliReporter(self.env, verbosity=self.verbosity):
            self.build(update_source_info_first=True)
            with Watcher(self.env, self.output_path) as watcher:
                for ts, _, _ in watcher:
                    if self.last_build is None or ts > self.last_build:
                        self.build()


class DevTools:
    """This builds the admin frontend (in watch mode)."""

    def __init__(self, env):
        self.watcher = None
        self.env = env

    def start(self):
        if self.watcher is not None:
            return

        frontend = os.path.join(os.path.dirname(__file__), "..", "frontend")
        portable_popen(["npm", "install"], cwd=frontend).wait()
        self.watcher = portable_popen(["npm", "run", "dev"], cwd=frontend)

    def stop(self):
        if self.watcher is None:
            return
        self.watcher.kill()
        self.watcher.wait()
        self.watcher = None


def browse_to_address(addr):
    # pylint: disable=import-outside-toplevel
    import webbrowser

    def browse():
        time.sleep(1)
        webbrowser.open("http://%s:%s" % addr)

    t = threading.Thread(target=browse)
    t.daemon = True
    t.start()


def run_server(
    bindaddr,
    env,
    output_path,
    prune=True,
    verbosity=0,
    lektor_dev=False,
    ui_lang="en",
    browse=False,
    extra_flags=None,
):
    """This runs a server but also spawns a background process.  It's
    not safe to call this more than once per python process!
    """
    wz_as_main = os.environ.get("WERKZEUG_RUN_MAIN") == "true"
    in_main_process = not lektor_dev or wz_as_main
    extra_flags = process_extra_flags(extra_flags)
    if lektor_dev:
        env.jinja_env.add_extension("jinja2.ext.debug")

    if in_main_process:
        background_builder = BackgroundBuilder(
            env,
            output_path=output_path,
            prune=prune,
            verbosity=verbosity,
            extra_flags=extra_flags,
        )
        background_builder.daemon = True
        background_builder.start()
        env.plugin_controller.emit(
            "server-spawn", bindaddr=bindaddr, extra_flags=extra_flags
        )

    app = WebAdmin(
        env,
        output_path=output_path,
        verbosity=verbosity,
        debug=lektor_dev,
        ui_lang=ui_lang,
        extra_flags=extra_flags,
    )

    dt = None
    if lektor_dev and not wz_as_main:
        dt = DevTools(env)
        dt.start()

    if browse:
        browse_to_address(bindaddr)

    try:
        return run_simple(
            bindaddr[0],
            bindaddr[1],
            app,
            use_debugger=True,
            threaded=True,
            use_reloader=lektor_dev,
            request_handler=WSGIRequestHandler
            if lektor_dev
            else SilentWSGIRequestHandler,
        )
    finally:
        if dt is not None:
            dt.stop()
        if in_main_process:
            env.plugin_controller.emit("server-stop")
