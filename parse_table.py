#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

from stream_handler import *


class ProductionRule(object):
    def __init__(self):
        self.__productions = []

    def productions(self):
        return self.__productions

    def apply_symbols(self, symbols):
        self.__productions = symbols

    def __str__(self):
        return "".join(map(str, self.__productions))


class Terminal(ProductionRule):
    pass


def match_string(s):
    class TerminalString(Terminal):
        def __eq__(self, other):
            return s == other

        def __str__(self):
            return s

    return TerminalString


class Letter(ProductionRule):
    def __eq__(self, other):
        return str(self) == str(other)


def is_terminal(symbol):
    return isinstance(symbol, Terminal)


PARSE_TABLE = {
}


def table_parse(stream, starting_rule):
    stack = [starting_rule()]
    head = stack[-1]
    while stack:
        top_symbol = stack[-1]
        current_token = stream.peek(1)[0]

        if is_terminal(top_symbol):
            assert top_symbol == current_token
            stream.pop_char()
            stack.pop()
        else:
            symbols = PARSE_TABLE.get((top_symbol, current_token), None)
            if symbols:
                top_symbol.apply_symbols(symbols)
                stack.pop()
                stack += symbols
            else:
                raise RuntimeError("Unable to handle token '{}'.".format(current_token))
    return head


def main():
    print(table_parse(StreamHandler.from_str("A"), match_string("A")))

    return 0


if __name__ == "__main__":
    main()

