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

from .parser import Parser, ParseError
from .orregex import OrRegex
from collections import namedtuple
from typing import List
import re


HEADER_MACRO = b"HEADER"
PRIVATE_HEADER_MACRO = b"PRIVATE_HEADER"
ANY_HEADER_MACRO = b"ANY_HEADER"
HEADER_MACROS = [HEADER_MACRO, PRIVATE_HEADER_MACRO, ANY_HEADER_MACRO]

GUARD_COMMENT = b"@guard"
INCLUDE_COMMENT = b"@include"


class CFileParseError(ParseError):
    msg_header = "Error parsing C file"


DeclEnd = namedtuple("DeclEnd", ["position", "is_definition"])


class SimpleCParser(Parser):
    re_preproc_if = re.compile(rb"""
        (if|ifdef|ifndef) \s
    """, re.VERBOSE)

    re_preproc_next = OrRegex({
        "start": rb"^ [^\S\n]* \# (?: if|ifdef|ifndef) \s",
        "end": rb"^ [^\S\n]* \#endif\b",
    }, re.MULTILINE)

    re_rest_of_line = re.compile(rb"""
        (\\. | [^\\\n])* \n?
    """, re.VERBOSE)

    re_rest_of_string = re.compile(rb"""
        (\\. | [^\\"])* ["]
    """, re.VERBOSE | re.DOTALL)

    re_rest_of_char = re.compile(rb"""
        (\\. | [^\\'])* [']
    """, re.VERBOSE | re.DOTALL)

    re_source_line = re.compile(rb"""
        ^ [^\S\n]* \S+ .* $
    """, re.VERBOSE | re.MULTILINE)

    def __init__(self, text):
        super().__init__(text)
        self.comments = []
        self.preproc_ifs = []

    def raise_exc(self, message, line, col):
        raise CFileParseError.with_header(message, line, col)

    def read_rest_of_line(self):
        match = self.re_rest_of_line.match(self.text, self.i)
        match or self.error("Expected end of line")
        self.i = match.end()

    def read_until_match(self, string):
        while not self.accept(string):
            self.read_single()

    def line_comment(self):
        self.read_rest_of_line()

    def block_comment(self):
        while not self.accept(b"*/"):
            self.advance(1)

    def non_cond_preproc(self):
        try:
            self.i = self.text.index(b"\n", self.i)
        except ValueError:
            self.i = len(self.text)

    def cond_preproc(self):
        """Called when an if, ifdef, or ifndef preprocessor directive is found.
        """
        start = self.i
        self.read_rest_of_line()
        while True:
            extype, match = self.re_preproc_next.search(self.text, self.i)
            if match is None:
                self.error("Expected '#endif'")
            if extype == self.re_preproc_next.types.end:
                self.i = match.end()
                return (start, self.i)
            self.i = self.text.index(b"#", match.start())
            self.cond_preproc()
        raise RuntimeError("Unexpected end of loop")

    def preproc(self):
        """Called when a preprocessor directive is found.
        """
        match = self.re_preproc_if.match(self.text, self.i)
        if match is None:
            self.non_cond_preproc()
            return (self.i, None)
        return self.cond_preproc()

    def string_literal(self):
        match = self.re_rest_of_string.match(self.text, self.i)
        match or self.error("Unterminated string literal")
        self.i = match.end()

    def char_literal(self):
        match = self.re_rest_of_char.match(self.text, self.i)
        match or self.error("Unterminated character literal")
        self.i = match.end()

    def paren(self):
        self.read_until_match(b")")

    def brace(self):
        self.read_until_match(b"}")

    def bracket(self):
        self.read_until_match(b"]")

    def read_single(self):
        if self.accept(b"//"):
            self.line_comment()
            return

        if self.accept(b"/*"):
            self.block_comment()
            return

        func = {
            b"#": self.preproc,
            b'"': self.string_literal,
            b"'": self.char_literal,
            b"(": self.paren,
            b"{": self.brace,
            b"[": self.bracket
        }.get(self.get(1))
        self.advance(1)
        func and func()

    def find_var_decl_end(self) -> DeclEnd:
        """Find the end of a variable declaration, or the "=" in a variable
        definition.
        """
        while self.get(1) not in b"=;":
            self.read_single()
        is_def = self.get(1) == b"="
        self.advance(1)
        return DeclEnd(self.i - 1, is_def)

    def find_func_decl_end(self) -> DeclEnd:
        """Finds the end of a function declaration, or the "{" in a function
        definition.
        """
        while self.get(1) not in b"{;":
            self.read_single()
        is_def = self.get(1) == b"{"
        self.advance(1)
        return DeclEnd(self.i - 1, is_def)

    def add_comment(self, start_pos: int, end_pos: int):
        """Adds a comment to the list of comments in the C file.

        :param start_pos: The position of the start of the comment.
        :param end_pos: The position of the end of the comment.
          ``self.text[start_pos:end_pos]`` should evaluate to the entire
          text in the comment, excluding any comment terminators
          (`//`, ``/*``, or ``*/``).
        """
        self.comments.append((start_pos, end_pos))

    def top_block_comment(self):
        """Called when a top-level "/* ... */" comment is found.
        """
        start = self.i
        self.block_comment()
        self.add_comment(start, self.i - len(b"*/"))

    def top_line_comment(self):
        """Called when a top-level "// ..." comment is found.
        """
        start = self.i
        self.line_comment()
        self.add_comment(start, self.i - len(b"\n"))

    def top_preproc(self):
        """Called when a top-level preprocessor directive is found.
        """
        start, end = self.preproc()
        if end is None:
            return
        self.preproc_ifs.append((start, end))

    def parse_metadata_iter(self):
        if self.accept(b"/*"):
            self.top_block_comment()
            return

        if self.accept(b"//"):
            self.top_line_comment()
            return

        if self.accept(b"#"):
            self.top_preproc()
            return

        self.read_single()

    def parse_metadata(self):
        """Parses metadata (comments and preprocessor directives)
        in the C file.
        """
        while not self.done:
            self.parse_metadata_iter()

    def get_next_source_line(self) -> bytes:
        """Gets the next line that does not consist solely of whitespace.

        :returns: The text of the line.
        """
        match = self.re_source_line.search(self.text, self.i)
        if not match:
            return None
        return match.group(0)


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

    def get_header_chunks(self) -> List[bytes]:
        """Gets all of the header blocks (e.g., the text between
        ``#ifdef HEADER`` and ``#endif``).
        """
        chunks = []
        for start_pos, end_pos in self.preproc_ifs:
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
