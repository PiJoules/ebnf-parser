#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

from stream_handler import *

import string


class ProductionRule(object):
    def __init__(self, productions=None):
        self.__productions = productions or []

    def productions(self):
        return self.__productions

    def apply_symbols(self, symbols):
        self.__productions = symbols

    def __str__(self):
        return "".join(map(str, self.__productions))

    def __hash__(self):
        return hash(type(self))

    def match_and_apply(self, symbol):
        self.check(symbol)
        self.__productions = symbol

    def check(self, symbol):
        """Raises runtime error if the symbol does not match the rule."""
        raise NotImplementedError

    def get_rules(self, lookahead):
        raise NotImplementedError


class Terminal(ProductionRule):
    pass


def is_terminal(symbol):
    return isinstance(symbol, Terminal)


class AnyCharacter(Terminal):
    def check(self, symbol):
        if not symbol:
            raise RuntimeError("Expected literally any character. No character provided.")


"""
Builtins
"""

def terminal_string(s):
    class TerminalString(ProductionRule):
        def __init__(self, productions=None):
            super(TerminalString, self).__init__(productions=productions)
            if s:
                self.__expected_char = s[0]
            else:
                self.__expected_char = ""

        def get_rules(self, lookahead):
            expected = self.__expected_char
            if lookahead == expected:
                if len(s) == 1:
                    return [AnyCharacter()]
                else:
                    return [AnyCharacter(), terminal_string(s[1:])()]
            else:
                return None

    return TerminalString


"""
Custom rules
"""

class Letter(Terminal):
    def check(self, symbol):
        if not symbol:
            raise RuntimeError("Expected a letter. Found none.")

        if symbol not in string.ascii_letters:
            raise RuntimeError("Expected ascii letter. Found '{}'.".format(symbol))


class Digit(Terminal):
    def check(self, symbol):
        if not symbol.isdigit():
            raise RuntimeError("Expected digit. Found '{}'.".format(symbol))


class Symbol(Terminal):
    SYMBOLS = "[]{}()<>'\"=|.,;"

    def check(self, symbol):
        if not symbol:
            raise RuntimeError("Expected symbol. Found none.")

        if symbol not in self.SYMBOLS:
            raise RuntimeError("Expected one of the characters in '{}'. Found '{}'.".format(self.SYMBOLS, symbol))


class Identifier(ProductionRule):
    def get_rules(self, lookahead):
        return [Letter(), Letter()]


def table_parse(stream, starting_rule):
    if not stream:
        raise RuntimeError("Empty stream provided.")

    stack = [starting_rule()]
    head = stack[-1]

    while stack:
        top_rule = stack[-1]
        current_token = stream.peek(1)[0]

        if is_terminal(top_rule):
            top_rule.match_and_apply(current_token)
            stream.pop_char()
            stack.pop()
        else:
            symbols = top_rule.get_rules(current_token)
            if symbols is not None:
                top_rule.apply_symbols(symbols)
                stack.pop()
                stack += list(reversed(symbols))
            else:
                raise RuntimeError("Unable to handle token '{}' for rule '{}'. {}".format(current_token, type(top_rule).__name__, stream))

    if stream:
        raise RuntimeError("Stream was not exhausted: {}".format(stream))

    if stack:
        raise RuntimeError("Stack was not exhausted: {}".format([type(x).__name__ for x in stack]))

    return head


def test_rule(s, rule_cls):
    s = s.strip()
    prod = table_parse(StreamHandler.from_str(s), rule_cls)
    assert s == str(prod), "Expected '{}'. Found '{}'.".format(s, prod)


def main():
    test_rule("A", Letter)
    test_rule("9", Digit)
    test_rule("]", Symbol)
    test_rule("abc", terminal_string("abc"))
    test_rule("AB", Identifier)

    return 0


if __name__ == "__main__":
    main()

