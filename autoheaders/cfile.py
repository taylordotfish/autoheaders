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

from .cparser import SimpleCParser, DeclEnd
from itertools import islice
from typing import List
import math
import re


HEADER_MACRO = b"HEADER"
PRIVATE_HEADER_MACRO = b"PRIVATE_HEADER"
ANY_HEADER_MACRO = b"ANY_HEADER"
HEADER_MACROS = [HEADER_MACRO, PRIVATE_HEADER_MACRO, ANY_HEADER_MACRO]

GUARD_COMMENT = b"@guard"
INCLUDE_COMMENT = b"@include"


def remove_leading_indentation(bytestr: bytes):
    """Removes leading indentation (indentation common to all lines).
    """
    whitespace = re.match(rb"[ \t]*", bytestr).group(0)
    whitespace_re = re.escape(whitespace)
    return re.sub(rb"^" + whitespace_re, rb"", bytestr, flags=re.MULTILINE)


def normalize_indentation(bytestr: bytes, reference_line: bytes):
    """Normalizes indentation. The size of the indent in the ``reference_line``
    is measured. This indent size is used as the base indentation unit. Then,
    in the passed ``bytestr``, all of the indent sizes are measured, and if
    there are any gaps (e.g., if there are lines with an indent of one unit,
    and lines with an indent of three units, but no lines with an indent of
    two units), the indentation is repeatedly collapsed until there are no
    gaps.
    """
    match = re.match(rb"\t+ | [ ]+", reference_line or b"", re.VERBOSE)
    if not match:
        return remove_leading_indentation(bytestr)
    indentation_unit = match.group(0)

    lines = bytestr.splitlines(keepends=True)
    base_lines = []
    for line in lines:
        indent, base_line = re.fullmatch(
            rb"((?: %s)*) (.*) $" % (re.escape(indentation_unit),),
            line, re.DOTALL | re.VERBOSE,
        ).groups()
        base_lines.append((len(indent), base_line))

    indent_sizes = sorted(list({indent for indent, _ in base_lines}))
    indent_map = {size: new_size for new_size, size in enumerate(indent_sizes)}
    return b"".join(
        (indentation_unit * indent_map[indent_size]) + base_line
        for indent_size, base_line in base_lines
    )


class CSourceFile:
    def __init__(self, text, private=False):
        self.parser = SimpleCParser(text)
        self.parser.parse_metadata()
        self.private = private

    @property
    def text(self):
        return self.parser.text

    @property
    def comments(self):
        return self.parser.comments

    @property
    def preproc_ifs(self):
        return self.parser.preproc_ifs

    def line_to_pos(self, lineno):
        return self.parser.line_to_pos(lineno)

    def get_line_start(self, pos):
        return self.parser.get_line_start(pos)

    def get_line_end(self, pos):
        return self.parser.get_line_end(pos)

    def find_var_decl_end(self, startpos) -> DeclEnd:
        self.parser.setpos(startpos)
        return self.parser.find_var_decl_end()

    def find_func_decl_end(self, startpos) -> DeclEnd:
        self.parser.setpos(startpos)
        return self.parser.find_func_decl_end()

    def get_var_decl_start(self, lineno):
        start = self.line_to_pos(lineno)
        end, is_def = self.find_var_decl_end(start)
        return (self.text[start:end].strip(), is_def)

    def get_func_decl_start(self, lineno):
        start = self.line_to_pos(lineno)
        end, is_def = self.find_func_decl_end(start)
        return (self.text[start:end].strip(), is_def)

    def make_func_decl(self, def_lineno: int) -> bytes:
        """Makes a function declaration from a line containing a function
        definition.
        """
        decl_start, is_def = self.get_func_decl_start(def_lineno)
        next_line = self.parser.get_next_source_line()
        return (
            remove_leading_indentation(self.get_comment_before(def_lineno)) +
            normalize_indentation(decl_start, next_line) + b";\n"
        )

    def make_plain_var_decl(self, def_lineno: int) -> bytes:
        """Makes a ``(static) <type> <variable-name>;`` declaration
        from a line containing a variable definition or declaration.
        """
        decl_start, is_def = self.get_var_decl_start(def_lineno)
        return remove_leading_indentation(
            self.get_comment_before(def_lineno) + decl_start + b";\n",
        )

    def make_extern_var_decl(self, def_lineno: int) -> bytes:
        """Makes an ``extern <type> <variable-name>;`` declaration from
        a line containing a variable definition or declaration.
        """
        decl_start, is_def = self.get_var_decl_start(def_lineno)
        return remove_leading_indentation(
            self.get_comment_before(def_lineno) + b"extern " +
            decl_start + b";\n",
        )

    def get_comment_pos_before(self, pos):
        start, end = 0, len(self.comments)
        while start < end:
            middle = (start + end) // 2
            comment_start, comment_end = self.comments[middle]

            if comment_end < pos:
                start = middle + 1
                continue
            if comment_end > pos:
                end = middle
                continue
            start = end = middle
        return None if start < 1 else self.comments[start - 1]

    def get_comment_pos_directly_before(self, pos):
        comment_pos = self.get_comment_pos_before(pos)
        if comment_pos is None:
            return None
        start, end = comment_pos
        prev_line_start = self.get_line_start(self.get_line_start(pos) - 1)
        if prev_line_start > end:
            return None
        return comment_pos

    def get_min_comment_start_directly_before(self, pos):
        start = pos
        while True:
            comment_pos = self.get_comment_pos_directly_before(start)
            if comment_pos is None:
                break
            start, _ = comment_pos
        if start == pos:
            return None
        return start

    def get_comment_from_pos(self, comment_pos):
        start, end = comment_pos
        start = self.get_line_start(start)
        end = self.get_line_end(end) + 1
        return self.text[start:end]

    def get_comment_before(self, lineno: int) -> bytes:
        """Gets the comment, if any, before the specified line.
        """
        pos = self.line_to_pos(lineno)
        start = self.get_min_comment_start_directly_before(pos)
        if start is None:
            return b""
        start = self.get_line_start(start)
        end = self.get_line_start(pos)
        return self.text[start:end]

    def header_preproc_match(self, string):
        match = re.fullmatch(rb"ifdef (.*)", string)
        return match and match.group(1) in [
            ANY_HEADER_MACRO,
            PRIVATE_HEADER_MACRO if self.private else HEADER_MACRO,
        ]

    def get_header_chunks(
            self, start_lineno: int, end_lineno: int) -> List[bytes]:
        """Gets all of the header blocks (e.g., the text between
        ``#ifdef HEADER`` and ``#endif``) between two lines.

        :param start_lineno: The starting line number (inclusive).
        :param end_lineno: The ending line number (exclusive). ``None``
          represents the end of the file.
        """
        range_start = self.line_to_pos(start_lineno)
        range_end = (
            math.inf if end_lineno is None else self.line_to_pos(end_lineno)
        )

        chunks = []
        preproc_ifs = islice(
            self.preproc_ifs,
            self.parser.get_first_preproc_if_after(range_start), None,
        )

        for start_pos, end_pos in preproc_ifs:
            if not (range_start <= start_pos < range_end):
                break

            chunk_start = self.get_line_end(start_pos) + 1
            preproc_start = self.text[start_pos:chunk_start].strip()
            if not self.header_preproc_match(preproc_start):
                continue

            chunk_end = self.get_line_start(end_pos)
            chunk = self.text[chunk_start:chunk_end].strip(b"\n")
            chunks.append(remove_leading_indentation(chunk + b"\n"))
        return chunks

    def get_guard_name(self) -> bytes:
        """Looks for an include guard comment (of the form "@guard ...").

        :returns: The macro name specified in the comment, or ``None``.
        """
        for start_pos, end_pos in self.comments:
            comment_text = self.text[start_pos:end_pos].strip()
            if comment_text.startswith(GUARD_COMMENT + b" "):
                return comment_text.split(b" ", 1)[1]
        return None

    def is_in_preproc_cond(self, lineno: int):
        """Checks whether or not the specified line is in a preprocessor
        conditional.
        """
        pos = self.line_to_pos(lineno)
        for start_pos, end_pos in self.preproc_ifs:
            if start_pos <= pos < end_pos:
                return True
        return False
