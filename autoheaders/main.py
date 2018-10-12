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

from .autoheaders import __version__, generate_headers, AutoheadersOpts
from .errors import AutoheadersError
from collections import namedtuple
import os.path
import re
import sys

USAGE = """\
Usage:
  {0} [options] [--] <c-file>
  {0} -h | --help | --version

Arguments:
  <c-file>  The C source code file from which to generate the header.
            If "-", read from standard input (unless preceded by "--").

Options:
  -p --private  Generate a private header file containing static declarations.

  -o <file>     Write the header file to the specified file. If given after
                "-p", a private header is written. This option may be given
                twice: once before "-p", and once after. If not given, the
                header is written to standard output.

  -c <cpp-arg>  Pass arguments to the C preprocessor. Separate arguments with
                commas, or provide multiple "-c" options. Use "\\" to escape
                characters (e.g., -c 'option\\,with\\,commas'). NB: When the
                preprocessor runs, the current working directory is the
                parent directory of the C file.

  --debug       Run the program in debug mode. Exception tracebacks are shown.
""".rstrip()


def stderr(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def get_bin_name(argv):
    if argv and argv[0]:
        return os.path.basename(argv[0])
    return "autoheaders"


def usage(bin_name, exit_code: int = 1):
    """Prints program usage information and optionally exits.

    :param exit_code: The program's exit code. If ``None``, the program
    will not exit.
    """
    print(USAGE.format(bin_name))
    if exit_code is not None:
        sys.exit(exit_code)


def run(args: "ParsedArgs"):
    """Runs the program.

    :param args: The arguments for the program.
    """
    opts = AutoheadersOpts()
    opts.c_path = args.c_file
    opts.outpath = args.outfile
    opts.private_outpath = args.private_outfile
    opts.cpp_args = args.cpp_args
    opts.private = args.private
    generate_headers(opts)


def run_or_exit(args: "ParsedArgs", debug: bool = False):
    """Runs the program. If an error is encountered, it is printed
    and the program exits. Arguments are passed to :func:`run`.

    :param args: The arguments for the program.
    :param debug: Whether or not to run the program in debug mode.
    If true, full exception tracebacks will be shown when errors are
    encountered.
    """
    try:
        run(args)
    except AutoheadersError as e:
        if debug:
            raise
        stderr(e.message)
        sys.exit(1)
    except Exception:
        stderr(
            "Unexpected error occurred. The exception traceback "
            "is shown below:", end="\n\n",
        )
        raise


class ArgParseError(namedtuple("ArgParseError", "message")):
    def print(self, *, template="{}", default=None, file=sys.stderr):
        if self.message is not None:
            print(template.format(self.message), file=file)
        elif default is not None:
            print(default, file=file)


class ParsedArgs:
    """Parsed command-line arguments.
    """
    def __init__(self):
        self.private = False
        self.debug = False
        self.help = False
        self.version = False
        # If None, code is read from stdin.
        self.c_file = None
        self.cpp_args = []

        self.outfile = None
        self.private_outfile = None

        self.no_args = False
        self.parse_error = None


class ArgParser:
    """Parses command-line arguments.
    """
    def __init__(self, args):
        self.args = args
        self.index = 0
        self.positional_index = 0

        self.parsed = ParsedArgs()
        self.options_done = False
        self.end_early = False

    @property
    def arg(self):
        try:
            return self.args[self.index]
        except IndexError:
            return None

    @property
    def done(self):
        return self.end_early or self.index >= len(self.args)

    def advance(self):
        self.index += 1

    def error(self, message=None):
        self.parsed.parse_error = ArgParseError(message)
        self.end_early = True

    def parse_long_option(self, arg):
        body = arg[len("--"):]
        if body == "private":
            self.parsed.private = True
            return
        if body == "debug":
            self.parsed.debug = True
            return
        if body == "version":
            self.parsed.version = True
            self.end_early = True
            return
        if body == "help":
            self.parsed.help = True
            self.end_early = True
            return
        self.error("Unrecognized option: {}".format(arg))

    def get_short_opt_arg(self, opt_body, index):
        rest = opt_body[index+1:]
        if rest:
            return rest
        self.advance()
        return self.arg

    # Parses a "-c" option.
    def parse_cpp_arg(self, cpp_arg):
        if cpp_arg is None:
            self.error('Expected argument after "-c".')
            return
        self.parsed.cpp_args += [
            # Interpret backslash escapes.
            re.sub(r"\\(.)", r"\1", arg.group(1)) for arg in
            # Parse comma-separated options with backslash escapes.
            re.finditer(r"(?: ^|,) ((?: \\. | [^,])*)", cpp_arg, re.VERBOSE)
        ]

    # Parses a "-o" option.
    def parse_outfile(self, outfile):
        if not outfile:
            self.error('Expected argument after "-o".')
            return
        if self.parsed.private:
            self.parsed.private_outfile = outfile
            return
        self.parsed.outfile = outfile

    def parse_short_option_char(self, opt_body, index):
        char = opt_body[index]
        if char == "p":
            self.parsed.private = True
            return index + 1
        if char == "h":
            self.parsed.help = True
            self.end_early = True
            return index + 1
        if char == "c":
            self.parse_cpp_arg(self.get_short_opt_arg(opt_body, index))
            return len(opt_body)
        if char == "o":
            self.parse_outfile(self.get_short_opt_arg(opt_body, index))
            return len(opt_body)
        self.error("Unrecognized option: -{}".format(char))
        return index

    def parse_short_option(self, arg):
        body = arg[len("-"):]
        index = 0
        while index < len(body) and not self.done:
            index = self.parse_short_option_char(body, index)

    def try_parse_option(self):
        arg = self.arg
        if arg == "--":
            self.options_done = True
            return True
        if re.match(r"--[^-]", arg):
            self.parse_long_option(arg)
            return True
        if re.match(r"-[^-]", arg):
            self.parse_short_option(arg)
            return True
        return False

    def parse_positional(self):
        arg = self.arg
        if self.positional_index == 0:
            c_file = None if arg == "-" and not self.options_done else arg
            self.parsed.c_file = c_file
            return
        self.error("Unexpected positional argument: {}".format(arg))

    def parse_single(self):
        if not self.options_done and self.try_parse_option():
            return
        self.parse_positional()
        self.positional_index += 1

    def handle_end(self):
        parsed = self.parsed
        if self.end_early:
            return
        if self.index <= 0:
            parsed.no_args = True
            return
        if self.positional_index < 1:
            self.error("Missing required positional argument: <c-file>")
        if parsed.private and parsed.outfile and not parsed.private_outfile:
            stderr('Warning: "-p" has no effect on earlier "-o" option.')

    def parse(self):
        while not self.done:
            self.parse_single()
            self.advance()
        self.handle_end()
        return self.parsed


def main_with_argv(argv):
    bin_name = get_bin_name(argv)
    args = sys.argv[1:]
    parsed = ArgParser(args).parse()

    if parsed.parse_error is not None:
        parsed.parse_error.print()
        stderr('See "{} --help" for usage information.'.format(bin_name))
        sys.exit(1)
    if parsed.help or parsed.no_args:
        usage(bin_name, 0 if parsed.help else 1)
    if parsed.version:
        print(__version__)
        return
    run_or_exit(parsed, debug=parsed.debug)


def main():
    main_with_argv(sys.argv)
