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

"""
Processing performed before the C code is fed to the C preprocessor.
"""

from .orregex import OrRegex
from .errors import BaseParseError
from .cfile import INCLUDE_COMMENT, HEADER_MACROS
import re


class PreCPPParseError(BaseParseError):
    msg_header = "Error while parsing C file:"

    def __init__(self, message, coords):
        super().__init__(message)
        self.coords = coords

    @classmethod
    def with_header(cls, message, coords):
        lineno, colno = coords
        return cls(
            "{}\n".format(cls.msg_header) +
            "(at line {}, column {})\n".format(lineno, colno) +
            str(message), coords,
        )


def coords_from_pos(text, pos):
    lineno = text.count(b"\n", 0, pos) + 1
    line_start = text.rfind(b"\n", 0, pos) + 1
    colno = pos - line_start + 1
    return (lineno, colno)


class IncludeParser:
    """Parses ``#include`` statements in a C file.
    """

    regex = OrRegex({
        "string": rb"""
            ["] (?: [\\]? .)*? ["]
        """,

        "char": rb"""
            ['] (?: [\\]? .)*? [']
        """,

        "preproc": rb"""
            (?: ^ | (?<= \n))
            [^\S\n]* \# [^\n]*
        """,

        "line_comment": rb"""
            // [^\n]*
        """,

        "block_comment": rb"""
            /[*] .*? [*]/
        """
    }, re.DOTALL)

    preproc_if_regex = re.compile(rb"""
        (?: if | ifdef | ifndef)\s
    """, re.VERBOSE)

    preproc_endif_regex = re.compile(rb"""
        endif (?: \s | $)
    """, re.VERBOSE)

    preproc_include_regex = re.compile(rb"""
        include \s
    """, re.VERBOSE)

    preproc_header_block_regex = re.compile(
        rb"ifdef \s* (%s) \s* $" % (
            rb"|".join(map(re.escape, HEADER_MACROS)),
        ),
        re.VERBOSE | re.MULTILINE,
    )

    def __init__(self, text):
        self.text = text
        self.pos = 0
        self.preproc_level = 0
        self.preproc_is_header_block_stack = [False]
        self.includes = []

    def preproc_if(self, preproc_start):
        self.preproc_level += 1
        self.preproc_is_header_block_stack.append(bool(
            self.preproc_header_block_regex.match(self.text, preproc_start),
        ))

    def preproc_endif(self):
        self.preproc_level -= 1
        if self.preproc_level < 0:
            self.error("Found #endif without matching #if(def,ndef)")
        self.preproc_is_header_block_stack.pop()

    @property
    def in_header_block(self):
        return self.preproc_is_header_block_stack[-1]

    def parse_iter(self):
        extype, match = self.regex.search(self.text, self.pos)
        if extype is None:
            self.pos = len(self.text)
            return
        self.pos = match.end()

        if extype != self.regex.types.preproc:
            return
        preproc_start = self.text.index(b"#", match.start()) + 1

        if self.preproc_if_regex.match(self.text, preproc_start):
            self.preproc_if(preproc_start)
            return

        if self.preproc_endif_regex.match(self.text, preproc_start):
            self.preproc_endif()
            return

        if not self.preproc_include_regex.match(self.text, preproc_start):
            return
        if not self.in_header_block:
            self.includes.append((match.start(), self.pos))

    def parse(self):
        while self.pos < len(self.text):
            self.parse_iter()
        return self.includes

    def error(self, message, pos=None):
        if pos is None:
            pos = self.pos
        coords = coords_from_pos(self.text, self.pos)
        raise PreCPPParseError.with_header(message, coords)


keep_include_regex = re.compile(rb"""
    (
        (// \s* %s) |           # Matches, e.g., "// @include"
        (/[*] \s* %s \s* [*]/)  # Matches, e.g., "/* @include */"
    ) \s* $
""" % ((re.escape(INCLUDE_COMMENT),) * 2), re.VERBOSE)


def should_keep_include(line):
    return bool(keep_include_regex.search(line))


def replace_includes(text: bytes) -> bytes:
    """Replaces certain ``#include`` statements in C code.

    See "Header generation" in the README for exactly which ``#include``
    statements are removed.
    """
    includes = IncludeParser(text).parse()
    parts = []
    pos = 0
    for start, end in includes:
        if should_keep_include(text[start:end]):
            continue
        parts.append(text[pos:start])
        pos = end
    parts.append(text[pos:])
    return b"".join(parts)


def process_pre_cpp_text(text: bytes) -> bytes:
    """Processes C code before it is fed to the C preprocessor.
    """
    return replace_includes(text)
