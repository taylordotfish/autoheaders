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


class AutoheadersError(Exception):
    """Base autoheaders exception class.
    """
    def __init__(self, message):
        super().__init__(message)

    @property
    def message(self):
        return self.args[0]


class BaseParseError(AutoheadersError):
    pass


class AutoheadersFileNotFoundError(AutoheadersError):
    @classmethod
    def from_filename(cls, filename):
        return cls("File not found: {}".format(filename))


class AutoheadersFileWriteError(AutoheadersError):
    @classmethod
    def from_filename(cls, filename):
        return cls("Could not write to file: {}".format(filename))
