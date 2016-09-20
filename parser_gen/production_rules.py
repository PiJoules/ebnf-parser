#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

from stream_handler import *

import string
import json


K = 1


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
    def matches(cls, *lookaheads):
        """Returns true if this symbaol can match to this rule. False otherwise."""
        return cls.get_rules(*lookaheads) is not None

    @classmethod
    def get_rules(cls, *lookaheads):
        raise NotImplementedError


"""
Builtins
"""

class StringRule(ProductionRule):
    """Rule for literal strings and characters."""
    def json(self):
        return "".join(p.json() for p in self.productions())


def terminal(s):
    class TerminalStringRule(StringRule):
        @classmethod
        def get_rules(cls, *lookaheads):
            expected = "" if not s else s[0]
            if lookaheads[0] == expected:
                return map(terminal, s)
            else:
                return None

        def json(self):
            return s

        def __str__(self):
            return s

        def __eq__(self, other):
            return s == other

    return TerminalStringRule


class AnyCharacter(StringRule):
    @classmethod
    def get_rules(cls, *lookaheads):
        return [terminal(lookaheads[0])] if lookaheads[0] else None


def alternation(*args):
    class MaybeAlternation(ProductionRule):
        @classmethod
        def get_rules(cls, *lookaheads):
            for rule_cls in args:
                if rule_cls.matches(lookaheads[0]):
                    return [rule_cls]
            return None

        def json(self):
            assert len(self.productions()) == 1
            return self.productions()[0].json()

    return MaybeAlternation


def repetition(rule_cls):
    class Repetition(ProductionRule):
        @classmethod
        def get_rules(cls, *lookaheads):
            if rule_cls.matches(lookaheads[0]):
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
        def get_rules(cls, *lookaheads):
            if rule_cls.matches(lookaheads[0]):
                for other_rule_cls in args:
                    if other_rule_cls.matches(lookaheads[0]):
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
        def get_rules(cls, *lookaheads):
            if rule_cls.matches(lookaheads[0]):
                return [rule_cls]
            else:
                return []

        def json(self):
            prods = self.productions()
            if prods:
                assert len(prods) == 1
                return prods[0].json()

    return Optional


def concatenation(*args):
    class Concatentation(ProductionRule):
        @classmethod
        def get_rules(cls, *lookaheads):
            if args[0].matches(lookaheads[0]):
                return args
            else:
                return None

        def json(self):
            return [p.json() for p in self.productions()]

    return Concatentation


class Letter(StringRule):
    @classmethod
    def get_rules(cls, *lookaheads):
        if lookaheads[0] and lookaheads[0] in string.ascii_letters:
            return [terminal(lookaheads[0])]
        return None


class Digit(StringRule):
    @classmethod
    def get_rules(cls, *lookaheads):
        if lookaheads[0].isdigit():
            return [terminal(lookaheads[0])]
        return None


class Symbol(StringRule):
    SYMBOLS = "[]{}()<>'\"=|.,;"

    @classmethod
    def get_rules(cls, *lookaheads):
        if lookaheads[0] and lookaheads[0] in cls.SYMBOLS:
            return [terminal(lookaheads[0])]
        return None


class SingleWhitespace(StringRule):
    @classmethod
    def get_rules(cls, *lookaheads):
        if lookaheads[0].isspace():
            return [terminal(lookaheads[0])]
        return None


class Whitespace(repetition(SingleWhitespace)):
    """Multiple optional whitespace."""
    def json(self):
        return "".join(super(Whitespace, self).json())


"""
Custom rules provided by grammar
"""

class Identifier(ProductionRule):
    @classmethod
    def get_rules(cls, *lookaheads):
        if Letter.matches(lookaheads[0]):
            return [Letter, repetition(alternation(Letter, Digit, terminal("_")))]
        else:
            return None


class EscapeCharacter(ProductionRule):
    @classmethod
    def get_rules(cls, *lookaheads):
        if terminal("\\").matches(lookaheads[0]):
            return [terminal("\\"), AnyCharacter]
        else:
            return None


class Terminal(ProductionRule):
    @classmethod
    def get_rules(cls, *lookaheads):
        if terminal("'").matches(lookaheads[0]):
            return [
                terminal("'"),
                repetition(
                    alternation(
                        exclusion(AnyCharacter, terminal("'"), terminal("\\")),
                        EscapeCharacter
                    )
                ),
                terminal("'")
            ]
        elif terminal('"').matches(lookaheads[0]):
            return [
                terminal('"'),
                repetition(
                    alternation(
                        exclusion(AnyCharacter, terminal('"'), terminal("\\")),
                        EscapeCharacter
                    )
                ),
                terminal('"')
            ]
        else:
            return None


class Optional(ProductionRule):
    @classmethod
    def get_rules(cls, *lookaheads):
        if terminal("[").matches(lookaheads[0]):
            return [
                terminal("["),
                Whitespace,
                Alternation,
                Whitespace,
                terminal("]"),
            ]
        else:
            return None


class Repetition(ProductionRule):
    @classmethod
    def get_rules(cls, *lookaheads):
        if terminal("{").matches(lookaheads[0]):
            return [
                terminal("{"),
                Whitespace,
                Alternation,
                Whitespace,
                terminal("}"),
            ]
        else:
            return None


class Grouping(ProductionRule):
    @classmethod
    def get_rules(cls, *lookaheads):
        if terminal("(").matches(lookaheads[0]):
            return [
                terminal("("),
                Whitespace,
                Alternation,
                Whitespace,
                terminal(")")
            ]
        else:
            return None


class SingleProduction(ProductionRule):
    @classmethod
    def get_rules(cls, *lookaheads):
        if Identifier.matches(lookaheads[0]):
            return [Identifier]
        elif Terminal.matches(lookaheads[0]):
            return [Terminal]
        elif Optional.matches(lookaheads[0]):
            return [Optional]
        elif Repetition.matches(lookaheads[0]):
            return [Repetition]
        elif Grouping.matches(lookaheads[0]):
            return [Grouping]
        else:
            return None


class MaybeConcatenation(ProductionRule):
    @classmethod
    def get_rules(cls, *lookaheads):
        if terminal(",").matches(lookaheads[0]):
            return [terminal(","), Whitespace, SingleProduction, Whitespace]
        else:
            return None


class Concatenation(ProductionRule):
    @classmethod
    def get_rules(cls, *lookaheads):
        if SingleProduction.matches(lookaheads[0]):
            return [SingleProduction, Whitespace, repetition(MaybeConcatenation)]
        else:
            return None


class MaybeAlternation(ProductionRule):
    @classmethod
    def get_rules(cls, *lookaheads):
        if terminal("|").matches(lookaheads[0]):
            return [terminal("|"), Whitespace, Concatenation]
        else:
            return None


class Alternation(ProductionRule):
    @classmethod
    def get_rules(cls, *lookaheads):
        if Concatenation.matches(lookaheads[0]):
            return [Concatenation, Whitespace, repetition(MaybeAlternation)]
        else:
            return None


class Rule(ProductionRule):
    @classmethod
    def get_rules(cls, *lookaheads):
        if Identifier.matches(lookaheads[0]):
            return [
                Identifier,
                Whitespace,
                terminal("="),
                Whitespace,
                Alternation,
                Whitespace,
                terminal(";"),
                Whitespace
            ]
        else:
            return None


class Grammar(repetition(Rule)):
    pass


"""
End cursom rules
"""

