import errno
import json
import os
from collections import OrderedDict

from inifile import IniFile

from lektor.context import get_ctx
from lektor.utils import decode_flat_data
from lektor.utils import iter_dotted_path_prefixes
from lektor.utils import merge
from lektor.utils import resolve_dotted_value


def load_databag(filename):
    try:
        if filename.endswith(".json"):
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f, object_pairs_hook=OrderedDict)
        elif filename.endswith(".ini"):
            return decode_flat_data(IniFile(filename).items(), dict_cls=OrderedDict)
        else:
            return None
    except (OSError, IOError) as e:
        if e.errno != errno.ENOENT:
            raise
        return None


class Databags:
    def __init__(self, env):
        self.env = env
        self.root_path = os.path.join(self.env.root_path, "databags")
        self._known_bags = {}
        self._bags = {}
        try:
            for filename in os.listdir(self.root_path):
                if filename.endswith((".ini", ".json")):
                    self._known_bags.setdefault(filename.rsplit(".", -1)[0], []).append(
                        filename
                    )
        except OSError:
            pass

    def get_bag(self, name):
        sources = self._known_bags.get(name)
        if not sources:
            return None
        rv = self._bags.get(name)
        if rv is None:
            filenames = []
            rv = OrderedDict()
            for filename in sources:
                filename = os.path.join(self.root_path, filename)
                rv = merge(rv, load_databag(filename))
                filenames.append(filename)
            self._bags[name] = (rv, filenames)
        else:
            rv, filenames = rv

        ctx = get_ctx()
        if ctx is not None:
            for filename in filenames:
                ctx.record_dependency(filename)

        return rv

    def lookup(self, key):
        for prefix, local_key in iter_dotted_path_prefixes(key):
            bag = self.get_bag(prefix)
            if bag is not None:
                if local_key is None:
                    return bag
                return resolve_dotted_value(bag, local_key)
        return None
