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
        self.__apply_stream()

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

    def pop_char(self):
        self.__handler.pop_char()
        return self.__handler.char()

    def parse(self):
        """Set the values of the productions property."""
        raise NotImplementedError

    def __apply_stream(self):
        self.__productions = self.parse()

    def _raise_syntax_error(self, **kwargs):
        raise RuleSyntaxError.from_stream_handler(
            self.__handler,
            **kwargs
        )

    def __str__(self):
        return "".join(map(str, self.__productions))

    def productions(self):
        return self.__productions

    def json(self):
        if isinstance(self.__productions, str):
            v = self.__productions
        else:
            v = [x.json() for x in self.__productions]
        return {
            type(self).__name__: v
        }


"""
Helper rules
"""


def terminal_string(expected):
    class TerminalString(ProductionRule):
        def parse(self):
            copied_handler = copy.deepcopy(self.stream_handler())
            acc = ""
            for c in expected:
                found = self.pop_char()
                acc += found
                if found != c:
                    raise RuleSyntaxError.from_stream_handler(
                        copied_handler,
                        expected=expected,
                        found=found
                    )
            return acc

    return TerminalString


def optional(rule):
    class Optional(ProductionRule):
        def parse(self):
            productions = []
            copied_handler = copy.deepcopy(self.stream_handler())
            try:
                next_rule = rule(copied_handler)
            except RuleSyntaxError:
                pass
            else:
                self.stream_handler().update_from_handler(copied_handler)
                productions.append(next_rule)
            return productions

    return Optional


def alternation(*args):
    """Decorator for Alternation class."""
    class Alternation(ProductionRule):
        def parse(self):
            next_rule = None
            for rule_cls in args:
                copied_handler = copy.deepcopy(self.stream_handler())
                try:
                    next_rule = rule_cls(copied_handler)
                except RuleSyntaxError:
                    pass
                else:
                    self.stream_handler().update_from_handler(copied_handler)
                    break
            else:
                self._raise_syntax_error(expected=str(map(str, args)))

            return [next_rule]

    return Alternation


def repetition(rule):
    """Decorator for Repetition class."""
    class Repetition(ProductionRule):
        def parse(self):
            productions = []

            # Keep testing until run into error
            while True:
                copied = copy.deepcopy(self.stream_handler())
                try:
                    # alternation
                    next_rule = rule(copied)
                except RuleSyntaxError:
                    break
                else:
                    productions.append(next_rule)
                    self.stream_handler().update_from_handler(copied)

            return productions

    return Repetition


def concatenation(*args):
    """Decorator for Concatentation class."""
    class Concatentation(ProductionRule):
        def parse(self):
            productions = []

            for rule_cls in args:
                prod = rule_cls(self.stream_handler())
                productions.append(prod)

            return productions

    return Concatentation


def exclusion(base, *args):
    class Exclusion(ProductionRule):
        def parse(self):
            productions = []

            copied = copy.deepcopy(self.stream_handler())
            prod = base(copied)
            for excluded_rule in args:
                try:
                    excluded_rule(copy.deepcopy(self.stream_handler()))
                except RuleSyntaxError:
                    pass
                else:
                    self._raise_syntax_error(expected="{} excluding {}".format(base, excluded_rule))
            productions.append(prod)
            self.stream_handler().update_from_handler(copied)

            return productions

    return Exclusion


class SingleWhitespace(ProductionRule):
    def parse(self):
        char = self.pop_char()
        if not char.isspace():
            self._raise_syntax_error(expected="alphabetic character")
        return char


class Whitespace(repetition(SingleWhitespace)):
    pass


class AnyCharacter(ProductionRule):
    def parse(self):
        char = self.pop_char()
        if not char:
            self._raise_syntax_error(expected="a character")
        return char


