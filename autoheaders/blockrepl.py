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
Replaces blocks (code in braces) in preprocessed C code for faster parsing.
"""

from .errors import BaseParseError
from .orregex import OrRegex
import re


class BlockReplacementParseError(BaseParseError):
    msg_header = "Error while parsing preprocessed C file:"

    def __init__(self, message, pos):
        super().__init__(message)
        self.pos = pos

    @classmethod
    def with_header(cls, message, pos):
        return cls(
            "{}\n".format(cls.msg_header) +
            "(at position {} in buffer)\n".format(pos) +
            str(message), pos,
        )


def find_statement_end(text, pos):
    braces = 0
    for i in range(pos, len(text)):
        if text[i] == b"{"[0]:
            braces += 1
        elif text[i] == b"}"[0]:
            braces -= 1
        elif braces > 0:
            pass
        elif text[i] == b";"[0]:
            return i
    raise BlockReplacementParseError.with_header(
        "Reached end of file while searching for statement end", pos)


def find_closing_brace(text, pos):
    braces = 1
    for i in range(pos, len(text)):
        if text[i] == b"{"[0]:
            braces += 1
            continue
        if text[i] != b"}"[0]:
            continue
        braces -= 1
        if braces <= 0:
            return i
    raise BlockReplacementParseError.with_header(
        "Reached end of file while searching for closing brace", pos)


string_regex = re.compile(rb"""
    (?:
        (?:
            (?: ^ | (?<= \n))  # Start of line
            \s* \# [^\n]*      # Preprocessor directive
        )?
        [^"'\n]* \n?
    )*

    (?: (
        (["'])                 # String start (group 2)
        (?: [\\]? .)*?         # String contents
        \2                     # String end
    ) | $)
""", re.VERBOSE | re.DOTALL)


def get_strings(text):
    strings = []
    for match in string_regex.finditer(text):
        start, end = match.start(1), match.end(1)
        if start < 0:
            continue
        strings.append((start, end))
    return strings


def replace_strings(text: bytes) -> bytes:
    """Replaces string literals in C code.

    :param text: The code.
    :returns: The code with string literals replaced.
    """
    parts = []
    pos = 0
    for start, end in get_strings(text):
        parts.append(text[pos:start+1])
        parts.append(b"\n" * text.count(b"\n", start, end))
        parts.append(text[end-1:end])
        pos = end
    parts.append(text[pos:])
    return b"".join(parts)


class BlockParser:
    """Searches for blocks (code in braces) in C code.
    """

    regex = OrRegex({
        "typedef": rb"\b typedef \s",
        "struct": rb"\b struct \s",
        "enum": rb"\b enum \s",
        "union": rb"\b union \s",
        "openbrace": rb"{",
        "assignment": rb"\b = \b",
        "preproc": rb"^ \# .*? $ \n?",
    }, re.MULTILINE | re.DOTALL)

    def __init__(self, text):
        self.text = text
        self.pos = 0
        self.blocks = []

    def parse_iter(self):
        extype, match = self.regex.search(self.text, self.pos)
        if extype is None:
            self.pos = len(self.text)
            return
        self.pos = match.end()

        if extype in self.statement_types:
            self.pos = find_statement_end(self.text, self.pos) + 1
            return

        if extype is self.regex.types.openbrace:
            end = find_closing_brace(self.text, self.pos)
            self.blocks.append((self.pos, end))
            self.pos = end
            return

    def parse(self):
        while self.pos < len(self.text):
            self.parse_iter()
        return self.blocks


BlockParser.statement_types = [BlockParser.regex.types[name] for name in [
    "typedef", "struct", "enum", "union", "assignment",
]]


non_preproc_regex = re.compile(rb"""
    (?: ^ | (?<= \n))  # Start of line
    [^#\n] [^\n]*?     # Non-preproc line
    (?: $ | (?= \n))   # End of line
""", re.VERBOSE)


def replace_non_preproc(text):
    return non_preproc_regex.sub(rb"", text)


def replace_blocks_from_list(text, blocks):
    parts = []
    pos = 0
    for start, end in blocks:
        parts.append(text[pos:start])
        parts.append(replace_non_preproc(text[start:end]))
        pos = end
    parts.append(text[pos:])
    return b"".join(parts)


def replace_blocks_nostr(text: bytes) -> bytes:
    """Replaces blocks without replacing string literals. Called by
    :func:`replace_blocks`.
    """
    blocks = BlockParser(text).parse()
    return replace_blocks_from_list(text, blocks)


def replace_blocks(text: bytes) -> bytes:
    """Replaces blocks (text in braces) in preprocessed C code for faster
    parsing. The code within the blocks is removed, but line numbers are
    preserved.
    """
    text = replace_strings(text)
    return replace_blocks_nostr(text)
