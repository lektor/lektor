import io

from setuptools import find_packages
from setuptools import setup

with io.open("README.md", "rt", encoding="utf8") as f:
    readme = f.read()

tests_require = [
    "pre-commit",
    "pylint==2.7.0",
    "pytest",
    "pytest-cov",
    "pytest-mock",
    "pytest-click",
]

setup(
    name="Lektor",
    use_scm_version=True,
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
    python_requires=">=3.6",
    setup_requires=["setuptools_scm"],
    install_requires=[
        "Babel",
        "click>=6.0",
        "EXIFRead",
        "filetype>=1.0.7",
        "Flask",
        "inifile",
        "Jinja2>=3.0",
        "mistune>=0.7.0,<2",
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
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    entry_points="""
        [console_scripts]
        lektor=lektor.cli:main
    """,
)
