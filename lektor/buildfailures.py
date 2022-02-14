import errno
import hashlib
import json
import os

from werkzeug.debug.tbtools import Traceback


class BuildFailure:
    def __init__(self, data):
        self.data = data

    @classmethod
    def from_exc_info(cls, artifact_name, exc_info):
        tb = Traceback(*exc_info)
        tb.filter_hidden_frames()
        return cls(
            {
                "artifact": artifact_name,
                "exception": tb.exception,
                "traceback": tb.plaintext,
            }
        )

    def to_json(self):
        return self.data


class FailureController:
    def __init__(self, pad, destination_path):
        self.pad = pad
        self.path = os.path.join(
            os.path.abspath(os.path.join(pad.db.env.root_path, destination_path)),
            ".lektor",
            "failures",
        )

    def get_filename(self, artifact_name):
        return (
            os.path.join(
                self.path, hashlib.md5(artifact_name.encode("utf-8")).hexdigest()
            )
            + ".json"
        )

    def lookup_failure(self, artifact_name):
        """Looks up a failure for the given artifact name."""
        fn = self.get_filename(artifact_name)
        try:
            with open(fn, "r", encoding="utf-8") as f:
                return BuildFailure(json.load(f))
        except IOError as e:
            if e.errno != errno.ENOENT:
                raise
            return None

    def clear_failure(self, artifact_name):
        """Clears a stored failure."""
        try:
            os.unlink(self.get_filename(artifact_name))
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise

    def store_failure(self, artifact_name, exc_info):
        """Stores a failure from an exception info tuple."""
        fn = self.get_filename(artifact_name)
        try:
            os.makedirs(os.path.dirname(fn))
        except OSError:
            pass
        with open(fn, mode="w", encoding="utf-8") as f:
            json.dump(BuildFailure.from_exc_info(artifact_name, exc_info).to_json(), f)
            f.write("\n")
