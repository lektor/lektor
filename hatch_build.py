import shutil
import subprocess
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class FrontendBuildHook(BuildHookInterface):
    def clean(self, versions):
        self.app.display_info("cleaning lektor/admin/static")
        target = Path(self.root, "lektor/admin/static")
        if target.is_dir():
            shutil.rmtree(target)

    def initialize(self, version, build_data):
        app = self.app
        target = "lektor/admin/static/app.js"
        if Path(self.root, target).is_file():
            app.display_info(f"{target} exists, skipping frontend build")
            return

        npm = shutil.which("npm")
        if npm is None:
            app.abort("npm is not available. can not build frontend")
        runopts = {
            "cwd": Path(self.root, "frontend"),
            "check": True,
        }
        app.display_info("npm install")
        subprocess.run((npm, "install"), **runopts)
        app.display_info("npm run build")
        subprocess.run((npm, "run", "build"), **runopts)
        app.display_success("built frontend static files")
