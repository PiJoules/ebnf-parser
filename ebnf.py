#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

from utils import SlotDefinedClass, base_parse_args, char_generator
from stream_handler import StreamHandler

import logging
import sys
import string
import itertools
import copy

LOGGER = logging.getLogger(__name__)


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
        return cls.from_whole_stream(StreamHandler(s))

    def _pop_char(self):
        self.__handler.pop_char()

    def _char(self):
        return self.__handler.char

    def _stream_handler(self):
        return self.__handler

    def _parse(self):
        """Set the values of the productions property."""
        raise NotImplementedError

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


class TerminatingString(ProductionRule):
    """Class for checking that a string is the next to come off the stream."""
    def __init__(self, stream_handler, expected):
        self.__expected = expected
        super(TerminatingString, self).__init__(stream_handler)

    def _parse(self):
        expected = self.__expected
        line_no = self._stream_handler().line_no
        col_no = self._stream_handler().col_no
        acc = ""
        for c in expected:
            acc += self._char()
            if self._char() != c:
                raise RuleSyntaxError(
                    line_no=line_no,
                    col_no=col_no,
                    expected=expected,
                    found=acc,
                )
            # Advance buffer
            self._stream_handler().pop_char()
        self.productions = acc

    @classmethod
    def try_to_create(cls, stream_handler, expected):
        try:
            copied_handler = copy.deepcopy(stream_handler)
            inst = cls(copied_handler, expected)
        except RuleSyntaxError:
            return None

        stream_handler.update(copied_handler)
        return inst


class Letter(ProductionRule):
    def _parse(self):
        if self._char() not in string.ascii_letters:
            self._raise_parse_error(expected="alphabetic character")
        self.productions = self._char()

        # Advance buffer
        self._pop_char()


class Digit(ProductionRule):
    def _parse(self):
        if not self._char().isdigit():
            self._raise_parse_error(expected="digit")
        self.productions = self._char()

        # Advance buffer
        self._pop_char()


class Symbol(ProductionRule):
    SYMBOLS = "[]{}()<>=|.,;'\""

    def _parse(self):
        if not self._char() in self.SYMBOLS:
            self._raise_parse_error(expected="one of the symbols '{}'".format(self.SYMBOLS))
        self.productions = self._char()

        # Advance buffer
        self._pop_char()


class OptionalWhitespace(ProductionRule):
    def _parse(self):
        productions = ""
        while self._char().isspace():
            productions += self._char()

            # Advance buffer
            self._pop_char()
        self.productions = productions


class Whitespace(ProductionRule):
    def _parse(self):
        productions = TerminatingString(self._stream_handler(), " ").productions
        self.productions = productions + OptionalWhitespace(self._stream_handler()).productions


class Identifier(ProductionRule):
    def _parse(self):
        letter = Letter(self._stream_handler())
        productions = [letter]

        # Test against letter, digit, or underscore
        while True:
            letter = Letter.try_to_create(self._stream_handler())
            if letter:
                productions.append(letter)
                continue

            digit = Digit.try_to_create(self._stream_handler())
            if digit:
                productions.append(digit)
                continue

            if self._char() == "_":
                productions.append("_")

                # Advance buffer
                self._pop_char()
                continue

            break

        self.productions = productions


class Character(ProductionRule):
    def _parse(self):
        production = (
            Letter.try_to_create(self._stream_handler()) or
            Digit.try_to_create(self._stream_handler()) or
            Symbol.try_to_create(self._stream_handler()) or
            TerminatingString.try_to_create(self._stream_handler(), "_")
        )
        if not production:
            self._raise_parse_error(expected="letter, digit, symbol, or _")
        self.productions = production.productions


class Terminal(ProductionRule):
    def _parse(self):
        open_quote = self._char()
        if not (open_quote == "\"" or open_quote == "'"):
            self._raise_parse_error(expected="either single or double quote")

        productions = open_quote
        self._pop_char()
        while self._char() != open_quote:
            # Handle escaped characters starting with backslash
            if self._char() == "\\":
                productions += self._char()
                self._pop_char()
            productions += self._char()
            self._pop_char()

        self.productions = productions + open_quote
        self._pop_char()


class Lhs(ProductionRule):
    def _parse(self):
        productions = []

        identifier = Identifier(self._stream_handler())
        productions.append(identifier)

        self.productions = productions


class Repetition(ProductionRule):
    def _parse(self):
        productions = []

        literal = TerminatingString(self._stream_handler(), "{")
        productions.append(literal.productions)

        spaces = OptionalWhitespace(self._stream_handler())

        rhs = Rhs(self._stream_handler())
        productions.append(rhs)

        OptionalWhitespace(self._stream_handler())

        literal = TerminatingString(self._stream_handler(), "}")
        productions.append(literal.productions)

        self.productions = productions


class Alternation(ProductionRule):
    def _parse(self):
        pass


class Rhs(ProductionRule):
    def _parse(self):
        # "{", rhs, "}"
        try:
            productions = []
            copied_handler = copy.deepcopy(self._stream_handler())

            productions.append(Repetition(copied_handler))

            self._stream_handler().update(copied_handler)
            self.productions = productions
            return
        except RuleSyntaxError:
            pass

        # terminal, ",", rhs
        try:
            productions = []
            copied_handler = copy.deepcopy(self._stream_handler())

            terminal = Terminal(copied_handler)
            productions.append(terminal)

            spaces = OptionalWhitespace(copied_handler)

            literal = TerminatingString(copied_handler, ",")
            productions.append(literal.productions)

            OptionalWhitespace(copied_handler)

            rhs = Rhs(copied_handler)
            productions.append(rhs)

            self._stream_handler().update(copied_handler)
            self.productions = productions
            return
        except RuleSyntaxError:
            pass

        # identifier, ",", rhs
        try:
            productions = []
            copied_handler = copy.deepcopy(self._stream_handler())

            identifier = Identifier(copied_handler)
            productions.append(identifier)

            spaces = OptionalWhitespace(copied_handler)

            literal = TerminatingString(copied_handler, ",")
            productions.append(literal.productions)

            OptionalWhitespace(copied_handler)

            rhs = Rhs(copied_handler)
            productions.append(rhs)

            self._stream_handler().update(copied_handler)
            self.productions = productions
            return
        except RuleSyntaxError:
            pass

        # terminal, "|", rhs
        try:
            productions = []
            copied_handler = copy.deepcopy(self._stream_handler())

            terminal = Terminal(copied_handler)
            productions.append(terminal)

            spaces = OptionalWhitespace(copied_handler)

            literal = TerminatingString(copied_handler, "|")
            productions.append(literal.productions)

            OptionalWhitespace(copied_handler)

            rhs = Rhs(copied_handler)
            productions.append(rhs)

            self._stream_handler().update(copied_handler)
            self.productions = productions
            return
        except RuleSyntaxError:
            #LOGGER.debug("failed on copied_handler: {}".format(copied_handler))
            pass

        # identifier, "|", rhs
        try:
            productions = []
            copied_handler = copy.deepcopy(self._stream_handler())

            identifier = Identifier(copied_handler)
            productions.append(identifier)

            spaces = OptionalWhitespace(copied_handler)

            literal = TerminatingString(copied_handler, "|")
            productions.append(literal.productions)

            OptionalWhitespace(copied_handler)

            rhs = Rhs(copied_handler)
            productions.append(rhs)

            self._stream_handler().update(copied_handler)
            self.productions = productions
            return
        except RuleSyntaxError:
            #LOGGER.debug("failed on copied_handler: {}".format(copied_handler))
            pass

        # identifier
        try:
            productions = []
            copied_handler = copy.deepcopy(self._stream_handler())

            identifier = Identifier(copied_handler)
            productions.append(identifier)

            self._stream_handler().update(copied_handler)
            self.productions = productions
            return
        except RuleSyntaxError:
            pass

        # terminal
        try:
            productions = []
            copied_handler = copy.deepcopy(self._stream_handler())

            terminal = Terminal(copied_handler)
            productions.append(terminal)

            self._stream_handler().update(copied_handler)
            self.productions = productions
            return
        except RuleSyntaxError:
            pass

        self._raise_parse_error(message="Unable to create right hand side of rule.")


class Rule(ProductionRule):
    def _parse(self):
        productions = []

        lhs = Lhs(self._stream_handler())
        print("lhs:", lhs)
        productions.append(lhs)

        optional_spaces = OptionalWhitespace(self._stream_handler())
        productions.append(optional_spaces)

        literal = TerminatingString(self._stream_handler(), "=")
        productions.append(literal)

        optional_spaces = OptionalWhitespace(self._stream_handler())
        productions.append(optional_spaces)

        rhs = Rhs(self._stream_handler())
        print("rhs:", rhs)
        productions.append(rhs)

        whitespace = OptionalWhitespace(self._stream_handler())
        productions.append(whitespace)

        literal = TerminatingString(self._stream_handler(), ";")
        productions.append(literal)

        self.productions = productions


class Grammar(ProductionRule):
    def _parse(self):
        productions = []
        rule = Rule.try_to_create(self._stream_handler())
        while rule:
            print("rule:", rule)
            productions.append(rule)

            whitespace = OptionalWhitespace(self._stream_handler())
            productions.append(whitespace)

            rule = Rule.try_to_create(self._stream_handler())
        self.productions = productions


def get_args():
    """Standard argument parser."""
    from argparse import ArgumentParser
    parser = ArgumentParser("Create a parse tree from a program with a grammar.")

    parser.add_argument("filename", help="Program to parse.")
    parser.add_argument("-g", "--grammar", required=True, help="Grammar file to use.")

    return base_parse_args(parser, name=__name__)


def main():
    args = get_args()

    grammar = Grammar.from_filename(args.filename)
    print(grammar)

    return 0


if __name__ == "__main__":
    main()

