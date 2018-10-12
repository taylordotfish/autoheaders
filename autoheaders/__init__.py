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

from . import blockrepl, cfile, errors, generator, parser
from .autoheaders import __version__, generate_headers
from .main import main, main_with_argv

# Silence Pyflakes
if False:
    assert [blockrepl, cfile, errors, generator, parser]
    assert [__version__, generate_headers]
    assert [main, main_with_argv]
