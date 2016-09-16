#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

from stream_handler import *

import string
import json


class ProductionRuleError(Exception):
    pass


class ProductionRule(object):
    def __init__(self, productions=None):
        self.__productions = productions or []

    def productions(self):
        return self.__productions

    def apply_rules(self, rules):
        self.__productions = rules

    def __str__(self):
        return "".join(map(str, self.__productions))

    def json(self):
        return {
            type(self).__name__: [x.json() if isinstance(x, ProductionRule) else x for x in self.__productions]
        }

    @classmethod
    def matches(cls, symbol):
        """Returns true if this symbaol can match to this rule. False otherwise."""
        return cls.get_rules(symbol) is not None

    @classmethod
    def get_rules(self, lookahead):
        raise NotImplementedError


"""
Builtins
"""

class StringRule(ProductionRule):
    """Rule for literal strings and characters."""
    def json(self):
        return "".join(self.productions())


class AnyCharacter(StringRule):
    @classmethod
    def get_rules(cls, lookahead):
        return [lookahead] if lookahead else None


def terminal_string(s):
    class TerminalStringRule(StringRule):
        @classmethod
        def get_rules(cls, lookahead):
            expected = "" if not s else s[0]
            if lookahead == expected:
                return list(s)
            else:
                return None

    return TerminalStringRule


def alternation(*args):
    class Alternation(ProductionRule):
        @classmethod
        def get_rules(cls, lookahead):
            for rule_cls in args:
                if rule_cls.matches(lookahead):
                    return [rule_cls]
            return None

        def json(self):
            assert len(self.productions()) == 1
            return self.productions()[0].json()

    return Alternation


def repetition(rule_cls):
    class Repetition(ProductionRule):
        @classmethod
        def get_rules(cls, lookahead):
            if rule_cls.matches(lookahead):
                return [rule_cls, repetition(rule_cls)]
            else:
                return []

        def repeating_rules(self, acc):
            prods = self.productions()
            if prods:
                assert len(self.productions()) == 2
                acc.append(prods[0].json())
                prods[1].repeating_rules(acc)

        def json(self):
            repetitions = []
            self.repeating_rules(repetitions)
            return repetitions

    return Repetition


def exclusion(rule_cls, *args):
    class Exclusion(ProductionRule):
        @classmethod
        def get_rules(cls, lookahead):
            if rule_cls.matches(lookahead):
                for other_rule_cls in args:
                    if other_rule_cls.matches(lookahead):
                        return None
                return [rule_cls]
            else:
                return None

        def json(self):
            prods = self.productions()
            assert len(prods) == 1
            return prods[0].json()

    return Exclusion


def optional(rule_cls):
    class Optional(ProductionRule):
        @classmethod
        def get_rules(cls, lookahead):
            if rule_cls.matches(lookahead):
                return [rule_cls]
            else:
                return []

        def json(self):
            prods = self.productions()
            if prods:
                assert len(prods) == 1
                return prods[0].json()

    return Optional


class Letter(StringRule):
    @classmethod
    def get_rules(cls, lookahead):
        if lookahead and lookahead in string.ascii_letters:
            return [lookahead]
        return None


class Digit(StringRule):
    @classmethod
    def get_rules(cls, lookahead):
        if lookahead.isdigit():
            return [lookahead]
        return None


class Symbol(StringRule):
    SYMBOLS = "[]{}()<>'\"=|.,;"

    @classmethod
    def get_rules(cls, lookahead):
        if lookahead and lookahead in cls.SYMBOLS:
            return [lookahead]
        return None


class SingleWhitespace(StringRule):
    @classmethod
    def get_rules(cls, lookahead):
        if lookahead.isspace():
            return [lookahead]
        return None


class Whitespace(repetition(SingleWhitespace)):
    """Multiple optional whitespace."""
    def json(self):
        return "".join(super(Whitespace, self).json())


"""
Custom rules provided by grammar
"""

PARSE_TABLE = {
}


class Identifier(ProductionRule):
    @classmethod
    def get_rules(cls, lookahead):
        if Letter.matches(lookahead):
            return [Letter, repetition(alternation(Letter, Digit, Symbol))]
        else:
            return None


class EscapeCharacter(ProductionRule):
    @classmethod
    def get_rules(cls, lookahead):
        if lookahead == "\\":
            return [terminal_string("\\"), AnyCharacter]
        else:
            return None


class Terminal(ProductionRule):
    @classmethod
    def get_rules(cls, lookahead):
        if lookahead == "'":
            return [
                terminal_string("'"),
                repetition(
                    alternation(
                        exclusion(AnyCharacter, terminal_string("'"), terminal_string("\\")),
                        EscapeCharacter
                    )
                ),
                terminal_string("'")
            ]
        elif lookahead == '"':
            return [
                terminal_string('"'),
                repetition(
                    alternation(
                        exclusion(AnyCharacter, terminal_string('"'), terminal_string("\\")),
                        EscapeCharacter
                    )
                ),
                terminal_string('"')
            ]
        else:
            return None


class Alternation(ProductionRule):
    pass


class Rule(ProductionRule):
    def get_rules(self, lookahead):
        if Identifier().matches(lookahead):
            return [
                Identifier(),
                Whitespace(),
                terminal_string("=")(),
                Whitespace(),
            ]
        else:
            return None


def table_parse(stream, starting_rule):
    stack = [starting_rule()]
    head = stack[-1]

    while stack:
        top_rule = stack.pop()
        current_token = stream.peek()

        if top_rule == current_token:
            stream.pop_char()
        else:
            rules = top_rule.get_rules(current_token)
            if rules is not None:
                rules = tuple(r if isinstance(r, str) else r() for r in rules)
                top_rule.apply_rules(rules)
                stack += list(reversed(rules))
            else:
                raise RuntimeError("Unable to handle token '{}' for rule '{}'. {}".format(current_token, type(top_rule).__name__, stream))

    if stack:
        raise RuntimeError("Stack was not exhausted: {}".format([type(x).__name__ for x in stack]))

    return head


def quick_prod(s, rule_cls, strip=True):
    s = s.strip() if strip else s
    return table_parse(StreamHandler.from_str(s), rule_cls)


def test_rule(s, rule_cls, strip=True, json=None):
    prod = quick_prod(s, rule_cls, strip=strip)
    assert s == str(prod), "Expected \"{}\". Found \"{}\".".format(s, prod)
    if json:
        assert prod.json() == json, "Expected \n{}\nFound\n{}".format(json, prod.json())


def print_rule(s, rule_cls, strip=True):
    prod = quick_prod(s, rule_cls, strip=strip)
    print(json.dumps(prod.json(), indent=4))


def main():
    test_rule("A", Letter, json="A")
    test_rule("9", Digit, json="9")
    test_rule("]", Symbol, json="]")
    test_rule("abc", terminal_string("abc"), json="abc")
    test_rule("", terminal_string(""), json="")
    test_rule("ABCD", Identifier, json={
        "Identifier": [
            "A",
            ["B", "C", "D"]
        ]
    })
    test_rule("ABC", repetition(Letter), json=["A", "B", "C"])
    test_rule("", repetition(Letter), json=[])
    test_rule("A", alternation(Letter, Digit, Symbol), json="A")
    test_rule("9", alternation(Letter, Digit, Symbol), json="9")
    test_rule(")", alternation(Letter, Digit, Symbol), json=")")
    test_rule(")89dfg", repetition(alternation(Letter, Digit, Symbol)), json=
        [")", "8", "9", "d", "f", "g"]
    )
    test_rule("a", exclusion(AnyCharacter, terminal_string("b")), json="a")
    test_rule("fkshff", repetition(exclusion(AnyCharacter, terminal_string("'"))), json=[
        "f", "k", "s", "h", "f", "f"
    ])
    test_rule("''", Terminal, json={
        "Terminal": ["'", [], "'"]
    })
    test_rule("\\s", EscapeCharacter, json={
        "EscapeCharacter": ["\\", "s"]
    })
    test_rule("'\\''", Terminal, json={
        "Terminal": [
            "'",
            [{
                "EscapeCharacter": ["\\", "'"]
            }],
            "'"
        ]
    })
    test_rule("'some string'", Terminal, json={
        "Terminal": ["'", list("some string"), "'"]
    })
    test_rule("'some \\string'", Terminal, json={
        "Terminal": ["'", list("some ") + [{"EscapeCharacter": ["\\", "s"]}] + list("tring"), "'"]
    })
    test_rule('"\\""', Terminal, json={
        "Terminal": [
            '"',
            [{
                "EscapeCharacter": ["\\", '"']
            }],
            '"'
        ]
    })
    test_rule('"some string"', Terminal, json={
        "Terminal": ['"', list("some string"), '"']
    })
    test_rule('"some \\string"', Terminal, json={
        "Terminal": ['"', list("some ") + [{"EscapeCharacter": ["\\", "s"]}] + list("tring"), '"']
    })
    test_rule("", optional(Digit), json="")
    test_rule("2", optional(Digit), json="2")
    test_rule(" ", SingleWhitespace, strip=False, json=" ")
    test_rule("\n", SingleWhitespace, strip=False, json="\n")
    test_rule("     ", Whitespace, strip=False, json="     ")

    # Fails on alternation of repetitions
    #test_rule("9", alternation(repetition(Letter), repetition(Digit), repetition(Symbol)))

    return 0


if __name__ == "__main__":
    main()

