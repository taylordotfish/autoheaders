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

from .cfile import CSourceFile
from .errors import BaseParseError

from pycparser import c_parser, c_ast, plyparser
import codecs
import locale
import re


class PycParseError(BaseParseError):
    def __init__(self, message, pyc_exc=None):
        self.pyc_exc = pyc_exc
        super().__init__(message)


class MetadataParseError(BaseParseError):
    pass


def get_default_encoding():
    encoding = locale.getpreferredencoding()
    try:
        codec = codecs.lookup(encoding)
    except LookupError:
        return "utf-8"
    if codec.name.lower() == "ascii":
        return "utf-8"
    return codec.name


def get_ast(preproc_str: str):
    parser = c_parser.CParser()
    try:
        return parser.parse(preproc_str)
    except plyparser.ParseError as e:
        raise PycParseError("Error parsing C file:\n{}".format(e), e) from e


def get_preproc_filename(preproc_str: str):
    match = re.match(r"""
        \s* \# \s* \d+? \s* "(.*?)"
    """, preproc_str, re.VERBOSE)
    if not match:
        raise MetadataParseError(
            'Expected to find source filename at the start of the '
            'preprocessed file (in the format: # 1 "<filename>")',
        )
    filename = match.group(1).replace(r'\"', r'"')
    return filename


class HeaderGenerator(c_ast.NodeVisitor):
    """Generates a header file from C code.

    :param c_text: The (non-preprocessed) C code.
    :param outfile: An open file object to which to write the generated header.
    :param private: Whether or not a private header file should be generated.
    """
    def __init__(self, c_text: bytes, outfile, private: bool = False):
        super().__init__()
        self.outfile = outfile
        self.private = private
        self.cfile = CSourceFile(c_text, private=private)

        self._decl = None
        self._first = True
        self._in_func_def = False
        self._preproc_filename = None
        self._ast = None

    def write_raw(self, text):
        self.outfile.write(text.replace(b"\r\n", b"\n"))

    def write_chunk(self, text):
        if not self._first:
            self.outfile.write(b"\n")
        self._first = False
        self.write_raw(text)

    def visit(self, node):
        if not self._preproc_filename:
            raise RuntimeError(
                "Source filename has not been set from preprocessed metadata",
            )
        matching_path = self._preproc_filename
        if node.coord is not None and node.coord.file != matching_path:
            return
        super().visit(node)

    def generic_visit(self, node):
        pass

    def visit_children(self, node):
        for _, child in node.children():
            self.visit(child)

    visit_FileAST = visit_children

    def visit_Decl(self, node):
        self._decl = node
        self.visit(node.type)

    def visit_PtrDecl(self, node):
        self.on_var_decl()

    def visit_TypeDecl(self, node):
        self.on_var_decl()

    def on_var_decl(self):
        if "extern" in self._decl.storage:
            return
        is_static = "static" in self._decl.storage
        if is_static != self.private:
            return

        lineno = self._decl.coord.line
        if not self.cfile.is_in_preproc_cond(lineno):
            self.write_chunk(
                self.cfile.make_plain_var_decl(lineno)
                if self.private else
                self.cfile.make_extern_var_decl(lineno)
            )

    def visit_FuncDecl(self, node):
        if not self._in_func_def:
            return
        self._in_func_def = False

        is_static = "static" in self._decl.storage
        if is_static != self.private:
            return
        lineno = self._decl.coord.line
        if not self.cfile.is_in_preproc_cond(lineno):
            self.write_chunk(self.cfile.make_func_decl(lineno))

    def visit_FuncDef(self, node):
        self._in_func_def = True
        self.visit(node.decl)
        self._in_func_def = False

    def load_ast_from_preprocessed(self, preprocessed):
        preproc_str = preprocessed.decode(get_default_encoding())
        self._ast = get_ast(preproc_str)
        self._preproc_filename = get_preproc_filename(preproc_str)

    def write_from_ast(self):
        self.visit(self._ast)

    def write_marked_chunks(self):
        for chunk in self.cfile.get_header_chunks():
            self.write_chunk(chunk)

    def write_guard_start(self, guard_name=None):
        if self.private:
            return False
        if guard_name is None:
            guard_name = self.cfile.get_guard_name()
        if guard_name is None:
            return False
        self.write_raw(b"#ifndef " + guard_name + b"\n")
        self.write_raw(b"#define " + guard_name + b"\n\n")
        return True

    def write_guard_end(self):
        if self.private:
            return
        self.write_raw(b"\n#endif\n")

    def write_all(self, preprocessed: bytes):
        """Writes a complete header file.

        :param preprocessed: The preprocessed C code.
        """
        self.load_ast_from_preprocessed(preprocessed)
        guard = self.write_guard_start()
        self.write_marked_chunks()
        self.write_from_ast()
        if guard:
            self.write_guard_end()
