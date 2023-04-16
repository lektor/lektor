from setuptools import setup

setup(
    name="lektor-dummy-plugin",
    description="setup.py test plugin",
    version="0.1a42",
    py_modules=["lektor_dummy_plugin"],
    entry_points={
        "lektor.plugins": [
            "dummy-plugin = lektor_dummy_plugin:DummyPlugin",
        ]
    },
)
