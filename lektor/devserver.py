import os
import time
import traceback
import threading

from werkzeug.serving import run_simple, WSGIRequestHandler

from lektor.db import Database
from lektor.builder import Builder, process_build_flags
from lektor.watcher import Watcher
from lektor.reporter import CliReporter
from lektor.admin import WebAdmin
from lektor.utils import portable_popen


_os_alt_seps = list(sep for sep in [os.path.sep, os.path.altsep]
                    if sep not in (None, '/'))


class SilentWSGIRequestHandler(WSGIRequestHandler):
    def log(self, type, message, *args):
        pass


class BackgroundBuilder(threading.Thread):

    def __init__(self, env, output_path, prune=True, verbosity=0,
                 build_flags=None):
        threading.Thread.__init__(self)
        watcher = Watcher(env, output_path)
        watcher.observer.start()
        self.env = env
        self.watcher = watcher
        self.output_path = output_path
        self.prune = prune
        self.verbosity = verbosity
        self.last_build = time.time()
        self.build_flags = build_flags

    def build(self, update_source_info_first=False):
        try:
            db = Database(self.env)
            builder = Builder(db.new_pad(), self.output_path,
                              build_flags=self.build_flags)
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
            for ts, _, _ in self.watcher:
                if self.last_build is None or ts > self.last_build:
                    self.build()


class DevTools(object):
    """This provides extra helpers for launching tools such as webpack."""

    def __init__(self, env):
        self.watcher = None
        self.env = env

    def start(self):
        if self.watcher is not None:
            return
        from lektor import admin
        admin = os.path.dirname(admin.__file__)
        portable_popen(['npm', 'install', '.'], cwd=admin).wait()

        self.watcher = portable_popen([os.path.join(
            admin, 'node_modules/.bin/webpack'), '--watch'],
            cwd=os.path.join(admin, 'static'))

    def stop(self):
        if self.watcher is None:
            return
        self.watcher.kill()
        self.watcher.wait()
        self.watcher = None


def browse_to_address(addr):
    import webbrowser
    def browse():
        time.sleep(1)
        webbrowser.open('http://%s:%s' % addr)
    t = threading.Thread(target=browse)
    t.setDaemon(True)
    t.start()


def run_server(bindaddr, env, output_path, prune=True, verbosity=0,
               lektor_dev=False, ui_lang='en', browse=False, build_flags=None):
    """This runs a server but also spawns a background process.  It's
    not safe to call this more than once per python process!
    """
    wz_as_main = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    in_main_process = not lektor_dev or wz_as_main
    build_flags = process_build_flags(build_flags)

    if in_main_process:
        background_builder = BackgroundBuilder(env, output_path=output_path,
                                               prune=prune, verbosity=verbosity,
                                               build_flags=build_flags)
        background_builder.setDaemon(True)
        background_builder.start()
        env.plugin_controller.emit('server-spawn', bindaddr=bindaddr,
                                   build_flags=build_flags)

    app = WebAdmin(env, output_path=output_path, verbosity=verbosity,
                   debug=lektor_dev, ui_lang=ui_lang,
                   build_flags=build_flags)

    dt = None
    if lektor_dev and not wz_as_main:
        dt = DevTools(env)
        dt.start()

    if browse:
        browse_to_address(bindaddr)

    try:
        return run_simple(bindaddr[0], bindaddr[1], app,
                          use_debugger=True, threaded=True,
                          use_reloader=lektor_dev,
                          request_handler=not lektor_dev
                          and SilentWSGIRequestHandler or WSGIRequestHandler)
    finally:
        if dt is not None:
            dt.stop()
        if in_main_process:
            env.plugin_controller.emit('server-stop')
