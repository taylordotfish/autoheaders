#!/usr/bin/env python3
# Copyright (C) 2016-2018, 2021 taylor.fish <contact@taylor.fish>
#
# This file is part of autoheaders.
#
# autoheaders is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# autoheaders is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with autoheaders.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys

SETUPTOOLS_IMPORT_ERROR_MSG = """\
setuptools must be installed. If pip is installed, run:
    sudo pip3 install setuptools
Or, to install locally:
    pip3 install --user setuptools
If pip isn't installed, see:
    https://pip.pypa.io/en/stable/installing/
Make sure the Python 3 version of pip (pip3) is installed.
""".rstrip()

try:
    from setuptools import setup
except ModuleNotFoundError:
    sys.exit(SETUPTOOLS_IMPORT_ERROR_MSG)

REPO_URL = "https://github.com/taylordotfish/autoheaders"
REPO_FILE_URL = "{}/blob/master".format(REPO_URL)
REPO_DIR_URL = "{}/tree/master".format(REPO_URL)

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
LICENSE_ID = "GNU General Public License v3 or later (GPLv3+)"


def repo_file_url_replacement(start, end):
    return (
        "{}{}".format(start, end),
        "{}{}/{}".format(start, REPO_FILE_URL, end),
    )


def repo_dir_url_replacement(start, end):
    return (
        "{}{}".format(start, end),
        "{}{}/{}".format(start, REPO_DIR_URL, end),
    )


DESC_REPLACEMENTS = dict([
    repo_file_url_replacement(".. _LICENSE: ", "LICENSE"),
    repo_file_url_replacement(".. _shim.h: ", "autoheaders/shim.h"),
    repo_dir_url_replacement(".. _example/: ", "example/"),
])


def long_description():
    with open(os.path.join(SCRIPT_DIR, "README.rst"), encoding='utf-8') as f:
        lines = f.read().splitlines()
    return "".join(
        DESC_REPLACEMENTS.get(line, line) + "\n"
        for line in lines
    )


setup(
    name="autoheaders",
    version="0.3.5",
    description="Automatically generate headers from C source code.",
    long_description=long_description(),
    url=REPO_URL,
    author="taylor.fish",
    author_email="contact@taylor.fish",
    license=LICENSE_ID,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Topic :: Internet",
        "License :: OSI Approved :: " + LICENSE_ID,
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    keywords="c header preprocessor",
    packages=["autoheaders"],
    entry_points={
        "console_scripts": [
            "autoheaders=autoheaders:main",
        ],
    },
    install_requires=[
        "pycparser>=2.18,<3",
        "setuptools>=39.0.0",
    ],
    python_requires=">=3.5",
    include_package_data=True,
    package_data={
        "autoheaders": ["autoheaders/shim.h"],
    },
)
