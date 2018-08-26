from enum import Enum
from typing import Dict, Any, Tuple
import re


class OrRegex:
    """A bytestring regular expression that is the disjunction of multiple
    regular expressions.

    :param expression_map: Maps a name to a regular expression pattern.
    For each name, an attribute with the name is added to the `types`
    attribute. Each of these sub-attributes in the `types` attribute is an
    enumeration value returned by :meth:`search`.
    """
    def __init__(self, expression_map: Dict[str, bytes], flags=0):
        expression_tuples = list(expression_map.items())
        type_names = [k for k, v in expression_tuples]
        expressions = [v for k, v in expression_tuples]

        """The types of regular expressions. Each sub-attribute of this
        attribute is a name specified in the ``expression_map`` parameter in
        the constructor. The value of each attribute is a unique enumeration
        value. These enumeration values are returned my :meth:`search`.
        """
        self.types = Enum("OrRegexType", type_names)

        self.type_list = list(self.types)
        self.regex = self.make_pattern(expressions, flags)

    def search(self, text: bytes, start: int = 0) -> Tuple[Enum, Any]:
        """Performs a search for any of the regular expressions provided
        during the construction of this object.

        :param text: The text in which to search.
        :param start: The position at which to start searching.
        :returns: A tuple, where the first item is the type of regular
          expression that was found (in the form of an enumeration value; see
          `types` and the ``expression_map`` parameter in the constructor for
          `OrRegex`), and the second item is the regex match object (as
          returned by :func:`re.match`).
        """
        match = self.regex.search(text, start)
        if match is None:
            return None, None

        groups = match.groups()
        if len(groups) != len(self.types):
            raise RuntimeError("Group count mismatch")

        i = 1
        while True:
            try:
                group_start = match.start(i)
            except IndexError as e:
                raise RuntimeError("No groups were matched") from e
            if group_start >= 0:
                return self.type_list[i - 1], match
            i += 1

    @classmethod
    def make_pattern(cls, expressions, flags):
        return re.compile(
            rb"|".join(b"(%s\n)" % (pattern,) for pattern in expressions),
            flags | re.VERBOSE,
        )
