from functools import update_wrapper
from itertools import chain

from flask import json
from flask import Response


def fs_path_to_url_path(path):
    segments = path.strip("/").split("/")
    if segments == [""]:
        segments = []
    segments.insert(0, "root")
    return ":".join(segments)


def eventstream(f):
    def new_func(*args, **kwargs):
        def generate():
            for event in chain(f(*args, **kwargs), (None,)):
                yield ("data: %s\n\n" % json.dumps(event)).encode()

        return Response(
            generate(), mimetype="text/event-stream", direct_passthrough=True
        )

    return update_wrapper(new_func, f)
