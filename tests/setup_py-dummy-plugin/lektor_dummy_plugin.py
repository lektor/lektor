"""Dummy test plugin"""
from lektor.pluginsystem import Plugin


class DummyPlugin(Plugin):
    """Dummy test plugin."""

    # pylint: disable=too-few-public-methods
    name = "dummy"
