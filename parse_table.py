#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

from stream_handler import *

import string


class ProductionRuleError(Exception):
    pass


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

    def check_and_apply(self, symbol):
        self.check(symbol)
        self.apply_symbols(symbol)

    def matches(self, symbol):
        """Returns true if this symbaol can match to this rule. False otherwise."""
        try:
            self.check(symbol)
        except ProductionRuleError:
            return False
        else:
            return True

    def check(self, symbol):
        """Raises runtime error if the symbol does not match the rule."""
        raise NotImplementedError

    def get_rules(self, lookahead):
        raise NotImplementedError


class TerminalRule(ProductionRule):
    pass


def is_terminal(symbol):
    return isinstance(symbol, TerminalRule)


class AnyCharacter(TerminalRule):
    def check(self, symbol):
        if not symbol:
            raise ProductionRuleError("Expected literally any character. No character provided.")


"""
Builtins
"""

def terminal_string(s):
    if s:
        expected = s[0]
    else:
        expected = ""

    class TerminalRuleString(ProductionRule):
        def get_rules(self, lookahead):
            if lookahead == expected:
                if len(s) == 1:
                    return [AnyCharacter()]
                elif not s:
                    return []
                else:
                    return [AnyCharacter(), terminal_string(s[1:])()]
            else:
                return None

        def check(self, lookahead):
            if self.get_rules(lookahead) is None:
                raise ProductionRuleError("Expected '{}' in terminal string. Found '{}'.".format(expected, lookahead))

    return TerminalRuleString


def alternation(*args):
    class Alternation(ProductionRule):
        def get_rules(self, lookahead):
            for rule_cls in args:
                rule = rule_cls()
                if rule.matches(lookahead):
                    return [rule]
            return None

        def check(self, symbol):
            for rule_cls in args:
                if rule_cls().matches(symbol):
                    break
            else:
                raise ProductionRuleError("Expected one of '{}'. Found '{}'.".format([x.__name__ for x in args], symbol))

    return Alternation


def repetition(rule_cls):
    class Repetition(ProductionRule):
        def get_rules(self, lookahead):
            rule = rule_cls()
            if rule.matches(lookahead):
                return [rule, repetition(rule_cls)()]
            elif not lookahead:
                return []
            else:
                return [rule]

        def check(self, symbol):
            # Really, repetition will match againnst anything since it could
            # be a length of zero
            pass

    return Repetition


def exclusion(rule_cls, *args):
    class Exclusion(ProductionRule):
        def get_rules(self, lookahead):
            rule = rule_cls()
            if rule.matches(lookahead):
                for other_rule_cls in args:
                    if other_rule_cls().matches(lookahead):
                        return None
                return [rule]
            else:
                return None

        def check(self, lookahead):
            rule_cls().check(lookahead)
            for other_rule_cls in args:
                if other_rule_cls().matches(lookahead):
                    raise ProductionRuleError("Expected '{}' but excluding '{}'. Found '{}'.".format(rule_cls, args, lookahead))

    return Exclusion


def concatenation(*args):
    class Concatentation(ProductionRule):
        def get_rules(self, lookahead):
            rules = [cls() for cls in args]
            if not rules:
                return []
            elif rules[0].matches(lookahead):
                # Continue with first rule
                if len(rules) == 1:
                    return [rules[0]]
                else:
                    return [rules[0], concatenation(*args[1:])()]
            else:
                return None

        def check(self, lookahead):
            pass

    return Concatentation


"""
Custom rules
"""

class Letter(TerminalRule):
    def check(self, symbol):
        if not symbol:
            raise ProductionRuleError("Expected a letter. Found none.")

        if symbol not in string.ascii_letters:
            raise ProductionRuleError("Expected ascii letter. Found '{}'.".format(symbol))


class Digit(TerminalRule):
    def check(self, symbol):
        if not symbol.isdigit():
            raise ProductionRuleError("Expected digit. Found '{}'.".format(symbol))


class Symbol(TerminalRule):
    SYMBOLS = "[]{}()<>'\"=|.,;"

    def check(self, symbol):
        if not symbol:
            raise ProductionRuleError("Expected symbol. Found none.")

        if symbol not in self.SYMBOLS:
            raise ProductionRuleError("Expected one of the characters in '{}'. Found '{}'.".format(self.SYMBOLS, symbol))


class Identifier(ProductionRule):
    def get_rules(self, lookahead):
        return [Letter(), repetition(alternation(Letter, Digit, Symbol))()]


class Terminal(ProductionRule):
    def get_rules(self, lookahead):
        #return [terminal_string("'")(), repetition(exclusion(AnyCharacter, terminal_string("'")))(), terminal_string("'")()]
        return [concatenation(
            terminal_string("'"),
            repetition(exclusion(AnyCharacter, terminal_string("'"))),
            terminal_string("'"),
        )()]


def table_parse(stream, starting_rule):
    stack = [starting_rule()]
    head = stack[-1]

    while stack:
        top_rule = stack[-1]
        current_token = stream.peek()

        if is_terminal(top_rule):
            top_rule.check_and_apply(current_token)
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
    test_rule("", terminal_string(""))
    test_rule("ABCHJGHJG", Identifier)
    test_rule("ABCHJGHJG", repetition(Letter))
    test_rule("", repetition(Letter))
    test_rule("A", alternation(Letter, Digit, Symbol))
    test_rule("9", alternation(Letter, Digit, Symbol))
    test_rule(")", alternation(Letter, Digit, Symbol))
    test_rule(")89dfg", repetition(alternation(Letter, Digit, Symbol)))
    test_rule("a", exclusion(AnyCharacter, terminal_string("b")))
    test_rule("fkshff", repetition(exclusion(AnyCharacter, terminal_string("'"))))
    test_rule("ab", concatenation(AnyCharacter, AnyCharacter))
    test_rule("''", Terminal)
    #test_rule("'some string'", Terminal)

    # Fails on alternation of repetitions
    #test_rule("9", alternation(repetition(Letter), repetition(Digit), repetition(Symbol)))

    return 0


if __name__ == "__main__":
    main()

