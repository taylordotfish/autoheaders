# Copyright (C) 2018 taylor.fish <contact@taylor.fish>
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

from .errors import AutoheadersError, AutoheadersFileNotFoundError
from .errors import AutoheadersFileWriteError
from .generator import HeaderGenerator
from .blockrepl import replace_blocks
from .precpp import process_pre_cpp_text

from typing import List
import pkg_resources
import os
import os.path
import shlex
import subprocess
import sys

__version__ = "0.3.3"

SHIM_NAME = "shim.h"


def get_shim_path() -> str:
    """Gets the path of shim.h.
    """
    return pkg_resources.resource_filename(__name__, SHIM_NAME)


class CPPLocationError(AutoheadersError):
    """Raised when the C preprocessor cannot be found.
    """
    pass


class CPPInvocationError(AutoheadersError):
    """Raised when an invocation of the C preprocessor is unsuccessful.
    """
    def __init__(self, message, subproc_exc=None):
        self.subproc_exc = subproc_exc
        super().__init__(message)


def cmd_in_path(cmd):
    return subprocess.run(
        ["which", cmd], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0


def find_fake_headers_dir(c_path: str) -> str:
    """Tries to find a .fake-headers/ directory. The directory containing the
    provided C file, as well as all parent directories, are searched.

    :param c_path: The path to the current C file.
    :returns: The path to the .fake-headers/ directory, or ``None``.
    """
    dirname = os.path.dirname(os.path.realpath(c_path or ""))
    while True:
        fake_headers_path = os.path.join(dirname, ".fake-headers")
        if os.path.isdir(fake_headers_path):
            return fake_headers_path

        next_dir = os.path.dirname(dirname)
        if next_dir == dirname:
            break
        dirname = next_dir
    return None


def get_cpp_fake_headers_args(c_path: str) -> List[str]:
    """Tries to find a .fake-headers/ directory, and if successful, returns
    additional arguments that can be passed to the C preprocessor to include
    the directory.

    :param c_path: The path to the current C file.
    :returns: Additional arguments to be passed to the C preprocessor.
      An empty list is returned if no .fake-headers/ directory was found.
    """
    dirname = find_fake_headers_dir(c_path)
    if dirname is None:
        return []
    return ["-I", dirname]


def get_base_cpp_args() -> List[str]:
    """Gets arguments to invoke the C preprocessor. Additional arguments
    can be appended to the returned list.

    :returns: Arguments that can be passed to `subprocess` functions to
    invoke the C preprocessor.
    """
    cpp = os.getenv("AUTOHEADERS_CPP")
    if cpp is not None:
        return shlex.split(cpp)
    if cmd_in_path("gcc"):
        return ["gcc", "-E"]
    if cmd_in_path("clang"):
        return ["clang", "-E"]
    raise CPPLocationError(
        "Could not find the C preprocessor.\n"
        "Try setting the AUTOHEADERS_CPP environment variable to a command\n"
        "that will invoke the preprocessor.\n"
        'For example: export AUTOHEADERS_CPP="/path/to/gcc -E"'
    )


def run_preprocessor(
        c_path: str, c_text: bytes, cpp_args: List[str] = None) -> bytes:
    """Runs the C preprocessor.

    :param c_path: The path to the current C file.
    :param c_text: The contents of the C file. This text may have already
      been processed (e.g., by :func:`precpp.process_pre_cpp_text`), but
      the line numbers should match the line numbers actually present in
      the C file.
    :param cpp_args: Additional arguments for the preprocessor.
    :returns: The preprocessed C code.
    """
    all_args = get_base_cpp_args()
    all_args.append("-")
    all_args += ["-include", get_shim_path()]
    all_args += ["-DHEADER", "-DPRIVATE_HEADER", "-DANY_HEADER"]
    all_args += get_cpp_fake_headers_args(c_path)
    all_args += (cpp_args or [])
    try:
        proc = subprocess.run(
            all_args, check=True, stdout=subprocess.PIPE, input=c_text,
        )
    except subprocess.CalledProcessError as e:
        raise CPPInvocationError(
            "Error running the C preprocessor.\n"
            "Command: " + " ".join(map(shlex.quote, e.cmd)), e
        ) from e
    except FileNotFoundError as e:
        raise CPPInvocationError(
            "Error running the C preprocessor: "
            "Could not locate executable: {}".format(all_args[0])
        ) from e
    return proc.stdout


def preprocess(
        c_path: str, c_text: bytes, cpp_args: List[str] = None) -> bytes:
    """Passes a C file to the C preprocessor after performing some initial
    processing (like removing certain ``#include`` statements).

    :param c_path: The path to the C file.
    :param c_text: The contents of the C file. This should match what is
      currently present in ``c_path``.
    :param cpp_args: Additional arguments for the preprocessor.
    :returns: The preprocessed C code.
    """
    chdir_success = c_path is not None
    if chdir_success:
        cwd = os.getcwd()
        try:
            os.chdir(os.path.dirname(c_path))
        except FileNotFoundError:
            chdir_success = False

    try:
        c_text = process_pre_cpp_text(c_text)
        c_text = run_preprocessor(c_path, c_text, cpp_args)
        return replace_blocks(c_text)
    finally:
        if chdir_success:
            os.chdir(cwd)


def _read_file(c_path):
    if c_path is None:
        return sys.stdin.buffer.read()
    try:
        with open(c_path, "rb") as f:
            return f.read()
    except FileNotFoundError as e:
        raise AutoheadersFileNotFoundError.from_filename(c_path) from e


class AutoheadersOpts:
    """Options for an invocation of autoheaders.

    Separate from command-line options; see `ParsedArgs`.
    """
    def __init__(self):
        # Path to the C file.
        self.c_path: str = None

        # Path to the destination for the regular header.
        self.outpath: str = None

        # Path to the destination for the private header.
        self.private_outpath: str = None

        # Additional arguments for the C preprocessor.
        self.cpp_args: List[str] = None

        # If neither outpath nor private_outpath is provided, this attribute
        # controls whether or not the header written to stdout is private.
        self.private: bool = False


def make_header_generator(opts: AutoheadersOpts):
    c_text = _read_file(opts.c_path)
    preprocessed = preprocess(opts.c_path, c_text, opts.cpp_args)
    return HeaderGenerator(c_text, preprocessed)


def _open_outfile(path: str):
    try:
        return open(path, "wb")
    except (FileNotFoundError, PermissionError) as e:
        raise AutoheadersFileWriteError.from_filename(path) from e


def generate_headers(opts: AutoheadersOpts):
    """Generates header files from a C source code file.

    :param opts: Options for this invocation of autoheaders.
    """
    gen = make_header_generator(opts)
    if not (opts.outpath or opts.private_outpath):
        gen.write_all(sys.stdout.buffer, private=opts.private)
        return

    if opts.outpath:
        with _open_outfile(opts.outpath) as f:
            gen.write_all(f, private=False)

    if opts.private_outpath:
        with _open_outfile(opts.private_outpath) as f:
            gen.write_all(f, private=True)
