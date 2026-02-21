"""A hatch build-hook that builds the front-end js/css at PEP 517 build time.

By default, when building the dist, if the built frontend code is not
present in the source directory, it will be built.  (Node must be installed,
or this will fail.)

Environment Variables
---------------------

There are a couple of environment variables that can be used to provide
additional control over the building of the frontend code.

- ``HATCH_BUILD_NO_HOOKS=true``: skip building the frontend code
- ``HATCH_BUILD_CLEAN=true``: force (re)building of the frontend code

"""

import shutil
import subprocess
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


# path to frontend source
FRONTEND = "frontend"

# path to compiled JS entry point
APP_JS = "lektor/admin/static/app.js"


class FrontendBuildHook(BuildHookInterface):
    """Hatching build hook to compile our frontend JS."""

    def clean(self, versions):
        """Called at the beginning of each PEP 517 build, if HATCH_BUILD_CLEAN is set.

        This implementation deletes any compiled frontend code that may be present
        in the source tree.
        """
        app = self.app
        root = self.root

        if not Path(root, FRONTEND).is_dir():
            app.display_info(
                "frontend source missing, skipping cleaning compiled output"
            )
            return

        output_path = Path(root, APP_JS).parent
        app.display_info(f"cleaning {output_path.relative_to(root)}")
        if output_path.is_dir():
            shutil.rmtree(output_path)

    def initialize(self, version, build_data):
        """Hook called before each package build.

        This implementation builds the compiled frontend source, but only
        if it is not already present in the source tree.

        Node (and npm) must be installed or this step will fail.
        """
        app = self.app
        root = self.root

        if Path(root, APP_JS).is_file():
            app.display_info(f"{APP_JS} exists, skipping frontend build")
            return

        try:
            proc = subprocess.run(
                "npm -v", capture_output=True, text=True, shell=True, check=True
            )
        except subprocess.CalledProcessError as exc:
            app.abort(f"{exc.cmd!r} failed (is node/npm installed?)")
        app.display_info(f"found npm version {proc.stdout.strip()}")

        frontend = Path(root, FRONTEND)
        if not frontend.is_dir():
            app.abort("frontend source is missing. can not build frontend")

        app.display_info("npm install --no-save")
        subprocess.run("npm install --no-save", cwd=frontend, shell=True, check=True)
        app.display_info("npm run build")
        subprocess.run("npm run build", cwd=frontend, shell=True, check=True)
        app.display_success("built frontend static files")
