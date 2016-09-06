# -*- coding: utf-8 -*-

from utils import SlotDefinedClass, char_generator
from stream_handler import StreamHandler

import copy

"""
definition: =
concatenation: ,
termination: ;
alternation: |
optional: [...]
repetition: {...}
grouping: (...)
terminal string: "..."
terminal string: '...'
comment: (*...*)
exception: -
"""


class ParseError(Exception):
    """Called when an error is found while parsing."""
    pass


class RuleSyntaxError(Exception):
    def __init__(self, line_no, col_no, expected=None, found=None, message=None):
        if expected:
            expected = expected.replace("\n", "\\n")
        if found:
            found = found.replace("\n", "\\n")
        msg = "Unable to parse token on line {}, col {}.".format(line_no, col_no)
        if message:
            msg += " {}".format(message)
        else:
            if expected:
                msg += " Expected {}.".format(expected)
            if found:
                msg += " Found '{}'.".format(found)
        super(RuleSyntaxError, self).__init__(msg)

    @classmethod
    def from_stream_handler(cls, stream_handler, **kwargs):
        return cls(stream_handler.line_no, stream_handler.col_no, **kwargs)


class ProductionRule(SlotDefinedClass):
    """
    This declaration is only here so I can use this class in
    the __types__ tuple.
    """
    pass


class ProductionRule(SlotDefinedClass):
    __types__ = ([(ProductionRule, str)], )
    __slots__ = ("productions", )

    RULES = tuple()

    def __init__(self, stream_handler):
        self.__handler = stream_handler
        self._parse()

    @classmethod
    def from_whole_stream(cls, stream_handler):
        """
        Asserts that the entire stream is also exhausted. This is meant for
        production rules that take up the whole file or string.
        """
        inst = cls(stream_handler)
        if stream_handler.char:
            raise ParseError("Expected this rule to take up the whole stream. Cut off at line {}, col {}.".format(stream_handler.line_no, stream_handler.col_no))
        return inst

    @classmethod
    def from_filename(cls, filename):
        return cls.from_whole_stream(StreamHandler(char_generator(filename)))

    @classmethod
    def from_str(cls, s):
        return cls.from_whole_stream(StreamHandler(iter(s)))

    def _pop_char(self):
        self.__handler.pop_char()

    def _char(self):
        return self.__handler.char

    def _stream_handler(self):
        return self.__handler

    def _parse(self):
        """Set the values of the productions property."""
        raise NotImplementedError

    def __parse_all(self):
        """
        Attempt to prevent inifinite recursion and find the first match of
        a rule by testing each production against different sized partitions.
        """
        copied_handler = copy.deepcopy(self._stream_handler())

        # Creates 2nd partition
        for i in xrange(len(self.RULES)):
            # Create 1st partition of size i
            while copied_handler.char:
                first_part = copy.deepcopy(copied_handler)
                first_part.end = i

                # Advance remaining
                copied_handler.advance(i)

                # copied_handler is now the rest of the stream
        return first_part, copied_handler

    def _raise_parse_error(self, **kwargs):
        raise RuleSyntaxError.from_stream_handler(
            self._stream_handler(),
            found=self._char(),
            **kwargs
        )

    @classmethod
    def try_to_create(cls, stream_handler):
        """
        Create a copy of the handler, and try to make this construction
        off the copy. Returns None if unable to create.
        Updates the given stream handler if successfully able to create
        the rule.
        """
        try:
            copied_handler = copy.deepcopy(stream_handler)
            inst = cls(copied_handler)
        except RuleSyntaxError:
            return None

        stream_handler.update(copied_handler)
        return inst

    def __str__(self):
        return "".join(map(str, self.productions))


