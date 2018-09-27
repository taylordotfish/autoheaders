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

from .errors import BaseParseError
from bisect import bisect_right


def _build_line_map_gen(text):
    yield 0
    for i, char in enumerate(text):
        if char == b"\n"[0]:
            yield i + 1


def build_line_map(text):
    return list(_build_line_map_gen(text))


def bytes_repr(bytestr):
    try:
        return repr(bytestr.decode())
    except UnicodeDecodeError:
        pass
    return repr(bytestr)


class ParseError(BaseParseError):
    msg_header = "Parser error"

    def __init__(self, message, line, col):
        self.line = line
        self.col = col
        super().__init__(message)

    @classmethod
    def with_header(cls, message, line, col):
        return cls("{}:\nAt line {}, column {}:\n{}".format(
            cls.msg_header, line, col, message,
        ), line, col)


class Parser:
    """A generic bytestring parser.
    """
    def __init__(self, text):
        if not text.endswith(b"\n"):
            text += b"\n"
        self.text = text
        self.i = 0
        self.linemap = build_line_map(text)

    def line_to_pos(self, lineno):
        return self.linemap[max(lineno, 1) - 1]

    def pos_to_line(self, pos):
        lineno = bisect_right(self.linemap, pos)
        return lineno

    def get_line_start(self, pos):
        return self.text.rfind(b"\n", 0, pos) + 1

    def get_line_end(self, pos):
        try:
            return self.text.index(b"\n", pos)
        except ValueError:
            return len(self.text)

    @property
    def location(self):
        line = self.pos_to_line(self.i)
        col = self.i - self.line_to_pos(line) + 1
        return (line, col)

    @property
    def done(self):
        return self.i >= len(self.text)

    def advance(self, num):
        self.i += num

    def get_noerr(self, num):
        return self.text[self.i:self.i+num]

    def get(self, num):
        if self.done:
            self.error("Unexpected end of file")
        return self.get_noerr(num)

    def match_noerr(self, string):
        return self.text.startswith(string, self.i)

    def match(self, string):
        if self.done:
            self.error(
                "Unexpected end of file while searching for " +
                bytes_repr(string),
            )
        return self.match_noerr(string)

    def accept_noerr(self, string):
        if not self.match(string):
            return False
        self.advance(len(string))
        return True

    def accept(self, string):
        if self.done:
            self.error(
                "Unexpected end of file while searching for " +
                bytes_repr(string),
            )
        return self.accept_noerr(string)

    def error(self, message):
        line, col = self.location
        self.raise_exc(message, line, col)

    def raise_exc(self, message, line, col):
        raise ParseError.with_header(message, line, col)

    def expect(self, string):
        if not self.accept(string):
            self.error("Expected " + bytes_repr(string))

    def setpos(self, pos):
        self.i = pos
