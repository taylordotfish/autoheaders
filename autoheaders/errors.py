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
