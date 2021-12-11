import io

from setuptools import find_packages
from setuptools import setup

with io.open("README.md", "rt", encoding="utf8") as f:
    readme = f.read()

tests_require = [
    "pre-commit",
    "pylint",
    "pytest",
    "pytest-cov",
    "pytest-mock",
    "pytest-click<1",
]

setup(
    name="Lektor",
    version="3.2.3",
    url="http://github.com/lektor/lektor/",
    description="A static content management system.",
    long_description=readme,
    long_description_content_type="text/markdown",
    license="BSD",
    author="Armin Ronacher",
    author_email="armin.ronacher@active-4.com",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    platforms="any",
    install_requires=[
        "Babel",
        "click>=6.0",
        'enum34;python_version<"3.4"',
        "EXIFRead",
        "filetype>=1.0.7",
        "Flask",
        'functools32;python_version<"3.2.3"',
        "inifile>=0.4.1",
        "Jinja2>=2.11",
        "mistune>=0.7.0,<2",
        'pathlib2;python_version<"3.4"',
        "pip",
        "python-slugify",
        "requests[security]",
        "setuptools",
        "watchdog",
        "Werkzeug<3",
    ],
    tests_require=tests_require,
    extras_require={
        "ipython": ["ipython"],
        "test": tests_require,
    },
    classifiers=[
        "Framework :: Lektor",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    entry_points="""
        [console_scripts]
        lektor=lektor.cli:main
    """,
)
