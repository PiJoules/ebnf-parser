# -*- coding: utf-8 -*-

from __future__ import print_function

from utils import char_generator
from stream_handler import StreamHandler
from iterator_tools import ExtendedIterator

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
        return cls(stream_handler.line_no(), stream_handler.col_no(), **kwargs)


class ProductionRule(object):
    def __init__(self, stream_handler):
        self.__handler = stream_handler
        self.__productions = []
        self.parse()

    @classmethod
    def from_whole_stream(cls, stream):
        inst = cls(stream)
        if inst.stream_handler():
            raise ParseError("{} did not consume the entire stream {}.".format(cls.__name__, stream))
        return inst

    @classmethod
    def from_filename(cls, filename):
        return cls.from_whole_stream(StreamHandler(ExtendedIterator(char_generator(filename))))

    @classmethod
    def from_str(cls, s):
        return cls.from_whole_stream(StreamHandler(ExtendedIterator(iter(s))))

    def stream_handler(self):
        return self.__handler

    def _pop_char(self):
        self.__handler.pop_char()
        return self.__handler.char()

    def parse(self):
        """Set the values of the productions property."""
        raise NotImplementedError

    def _set_productions(self, productions):
        self.__productions = productions

    def __parse_all(self):
        """
        Attempt to prevent inifinite recursion and find the first match of
        a rule by testing each production against different sized partitions.
        """
        raise NotImplementedError

    def _raise_syntax_error(self, **kwargs):
        raise RuleSyntaxError.from_stream_handler(
            self.__handler,
            **kwargs
        )

    #@classmethod
    #def try_to_create(cls, stream_handler):
    #    """
    #    Create a copy of the handler, and try to make this construction
    #    off the copy. Returns None if unable to create.
    #    Updates the given stream handler if successfully able to create
    #    the rule.
    #    """
    #    try:
    #        copied_handler = copy.deepcopy(stream_handler)
    #        inst = cls(copied_handler)
    #    except RuleSyntaxError:
    #        return None

    #    stream_handler.update(copied_handler)
    #    return inst

    def __str__(self):
        return "".join(map(str, self.__productions))


