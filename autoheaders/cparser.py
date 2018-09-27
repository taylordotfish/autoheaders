from .parser import Parser, ParseError
from .orregex import OrRegex

from collections import namedtuple
import bisect
import re


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

    def get_first_preproc_if_after(self, pos: int) -> int:
        """Gets the index of the next preprocessor conditional after the
        specific position.
        """
        return bisect.bisect_left(self.preproc_ifs, (pos, 0))
