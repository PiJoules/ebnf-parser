#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

from utils import SlotDefinedClass, base_parse_args

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


def char_generator(filename):
    with open(filename, "r") as f:
        for line in f:
            for c in line:
                yield c


class ParseError(Exception):
    def __init__(self, line_no, col_no, expected=None, found=None):
        msg = "Unable to parse token on line {}, col {}.".format(line_no, col_no)
        if expected:
            msg += " Expected {}.".format(expected)
        if found:
            msg += " Found '{}'.".format(found)
        super(ParseError, self).__init__(msg)

    @classmethod
    def from_stream_handler(cls, stream_handler, **kwargs):
        return cls(stream_handler.line_no, stream_handler.col_no, **kwargs)


class StreamHandler(SlotDefinedClass):
    """Class for handling iterating through a stream of characters."""
    __types__ = (str, int, int)
    __slots__ = ("char", "line_no", "col_no", "char_iter")

    def __init__(self, char_iter):
        self.char_iter = char_iter
        self.line_no = 1
        self.col_no = 1
        self.__pop_without_increment()

    def __pop_without_increment(self):
        self.char = next(self.char_iter, "")

    def pop_char(self):
        """Get the next character and increment the location."""
        if self.char:
            if self.char == "\n":
                self.line_no += 1
                self.col_no = 1
            else:
                self.col_no += 1
            self.__pop_without_increment()

    def __copy_iter(self):
        char_iter = self.char_iter
        char_iter, copied_iter = itertools.tee(self.char_iter)
        self.char_iter = char_iter
        return copied_iter

    def peek_chars(self, n):
        """
        Get the next n items in the stream as a list. The current char is not
        part of this list.
        """
        copied_iter = self.__copy_iter()
        elems = itertools.islice(copied_iter, n)
        return list(elems)

    def __deepcopy__(self, memo):
        """
        Create a copy of the handler such that advancing this iterator
        will not advance the copied iterator.
        """
        copied_iter = self.__copy_iter()
        handler = StreamHandler(copied_iter)
        handler.update(self)
        return handler

    def update(self, handler):
        """Update the properties of this handler to match those of another."""
        super(StreamHandler, self).update(**handler.json())


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
    def from_filename(cls, filename):
        return cls(StreamHandler(char_generator(filename)))

    @classmethod
    def from_str(cls, s):
        return cls(StreamHandler(s))

    def _pop_char(self):
        self.__handler.pop_char()

    def _char(self):
        return self.__handler.char

    def _stream_handler(self):
        return self.__handler

    def _parse(self):
        """Set the values of the productions property."""
        raise NotImplementedError

    def _raise_parse_error(self, expected=None):
        raise ParseError.from_stream_handler(
            self._stream_handler(),
            expected=expected,
            found=self._char()
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
        except ParseError:
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
                raise ParseError(
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
        except ParseError:
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
    SYMBOLS = "[]{}()<>'\"=|.,;"

    def _parse(self):
        if not self._char() in self.SYMBOLS:
            self._raise_parse_error(expected="one of the symbols '{}'".format(self.SYMBOLS))
        self.productions = self._char()

        # Advance buffer
        self._pop_char()


class OptionalSpaces(ProductionRule):
    def _parse(self):
        productions = ""
        while self._char() == " ":
            productions += self._char()

            # Advance buffer
            self._pop_char()
        self.productions = productions


class Spaces(ProductionRule):
    def _parse(self):
        productions = TerminatingString(self._stream_handler(), " ").productions
        self.productions = productions + OptionalSpaces(self._stream_handler()).productions


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
        productions = []

        try:
            d_quote = TerminatingString(self._stream_handler(), '"').productions

            character = Character(self._stream_handler())
            print("character:", character)
        except ParseError:
            pass

        self.productions = productions


class Lhs(ProductionRule):
    def _parse(self):
        productions = []

        identifier = Identifier(self._stream_handler())
        productions.append(identifier)
        print("identifier:", identifier)

        optional_spaces = OptionalSpaces(self._stream_handler())
        productions.append(optional_spaces)
        print("optional_spaces:", optional_spaces)

        literal = TerminatingString(self._stream_handler(), "=").productions
        productions.append(literal)
        print("equals sign:", literal)

        optional_spaces = OptionalSpaces(self._stream_handler())
        productions.append(optional_spaces)
        print("optional_spaces:", optional_spaces)

        terminal = Terminal(self._stream_handler())
        productions.append(terminal)
        print("terminal:", terminal)

        self.productions = productions


class Rule(ProductionRule):
    def _parse(self):
        productions = []
        lhs = Lhs(self._stream_handler())
        self.productions = productions


class Grammar(ProductionRule):
    def _parse(self):
        productions = []
        rule = Rule(self._stream_handler())
        while rule:
            productions.append(rule)
            rule = Rule(self._stream_handler())
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

