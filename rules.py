#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

from production_rule import ProductionRule, RuleSyntaxError

import string
import copy


def match_string(expected):
    class TerminalString(ProductionRule):
        def parse(self):
            copied_handler = copy.deepcopy(self.stream_handler())
            acc = ""
            for c in expected:
                found = self._pop_char()
                acc += found
                if found != c:
                    raise RuleSyntaxError.from_stream_handler(
                        copied_handler,
                        expected=expected,
                        found=found
                    )
            self._set_productions(acc)
    return TerminalString


class Letter(ProductionRule):
    def parse(self):
        # Get char from buffer
        char = self._pop_char()
        if (not char) or (char not in string.ascii_letters):
            self._raise_syntax_error(expected="alphabetic character")
        self._set_productions(char)


class Symbol(ProductionRule):
    SYMBOLS = "[]{}()<>'\"=|.,;"

    def parse(self):
        # Get char from buffer
        char = self._pop_char()
        if (not char) or (char not in self.SYMBOLS):
            self._raise_syntax_error(expected="one of the characters '{}'".format(self.SYMBOLS))
        self._set_productions(char)


class Digit(ProductionRule):
    def parse(self):
        char = self._pop_char()
        if not char.isdigit():
            self._raise_syntax_error(expected="alphabetic character")
        self._set_productions(char)


class AnyCharacter(ProductionRule):
    def parse(self):
        char = self._pop_char()
        if not char:
            self._raise_syntax_error(expected="a character")
        self._set_productions(char)


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

            self._set_productions([next_rule])
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

            self._set_productions(productions)
    return Repetition


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
            self._set_productions(productions)

    return Optional


def count_diff(h1, h2):
    return h1.char_iter().count() - h2.char_iter().count()


def concatenation(*args):
    """Decorator for Concatentation class."""
    class Concatentation(ProductionRule):
        def parse(self):
            productions = []

            for rule_cls in args:
                prod = rule_cls(self.stream_handler())
                productions.append(prod)

            self._set_productions(productions)

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

            self._set_productions(productions)

    return Exclusion


class Terminal(ProductionRule):
    def parse(self):
        # "'", character, { character }, "'"
        # '"', character, { character }, '"'
        self._set_productions([
            alternation(
                concatenation(
                    match_string("'"),
                    AnyCharacter,
                    repetition(exclusion(AnyCharacter, match_string("'"))),
                    match_string("'")
                ),
                concatenation(
                    match_string('"'),
                    AnyCharacter,
                    repetition(exclusion(AnyCharacter, match_string('"'))),
                    match_string('"')
                )
            )(self.stream_handler())
        ])


class Identifier(ProductionRule):
    def parse(self):
        # Letter, { Letter, Digit, "_" }
        alt = alternation(Letter, Digit, match_string("_"))
        rep = repetition(alt)
        self._set_productions([concatenation(Letter, rep)(self.stream_handler())])


class SingleWhitespace(ProductionRule):
    def parse(self):
        char = self._pop_char()
        if not char.isspace():
            self._raise_syntax_error(expected="alphabetic character")
        self._set_productions(char)


class Whitespace(repetition(SingleWhitespace)):
    pass


class Optional(ProductionRule):
    def parse(self):
        self._set_productions([
            concatenation(
                match_string("["),
                Whitespace,
                Productions,
                Whitespace,
                match_string("]")
            )(self.stream_handler())
        ])


class Repetition(ProductionRule):
    def parse(self):
        self._set_productions([
            concatenation(
                match_string("{"),
                Whitespace,
                Productions,
                Whitespace,
                match_string("}"),
            )(self.stream_handler())
        ])


class Grouping(ProductionRule):
    def parse(self):
        self._set_productions([
            concatenation(
                match_string("("),
                Whitespace,
                Productions,
                Whitespace,
                match_string(")")
            )(self.stream_handler())
        ])


class SingleRule(ProductionRule):
    def parse(self):
        self._set_productions([
            alternation(
                Identifier,
                Terminal,
                Optional,
                Repetition,
                Grouping,
            )(self.stream_handler())
        ])


class Concatentation(ProductionRule):
    def parse(self):
        self._set_productions([
            alternation(
                concatenation(
                    SingleRule,
                    Whitespace,
                    match_string(","),
                    Whitespace,
                    Concatentation
                ),
                SingleRule
            )(self.stream_handler())
        ])


class Alternation(ProductionRule):
    def parse(self):
        self._set_productions([
            alternation(
                concatenation(
                    Concatentation,
                    Whitespace,
                    match_string("|"),
                    Whitespace,
                    Alternation
                ),
                Concatentation
            )(self.stream_handler())
        ])


class Productions(ProductionRule):
    def parse(self):
        self._set_productions([
            Alternation(self.stream_handler())
        ])


class Rule(ProductionRule):
    def parse(self):
        self._set_productions([
            concatenation(
                Identifier,
                Whitespace,
                match_string("="),
                Whitespace,
                Productions,
                Whitespace,
                match_string(";"),
                Whitespace
            )(self.stream_handler())
        ])


class Grammar(ProductionRule):
    def parse(self):
        self._set_productions([
            repetition(Rule)(self.stream_handler())
        ])


def test_rule(test, rule_cls):
    test = test.strip()
    x = str(rule_cls.from_str(test))
    assert x == test, "Expected {}, found '{}'.".format(test, x)


def main():
    test_rule("A", Letter)
    test_rule("9", Digit)
    test_rule("[", Symbol)
    test_rule("literal", match_string("literal"))
    test_rule("AAA_9__9", Identifier)
    test_rule("'something'", Terminal)
    test_rule('"something"', Terminal)
    test_rule("   ", Whitespace)
    test_rule("'something' name", concatenation(Terminal, Whitespace, Identifier))
    test_rule("", optional(AnyCharacter))
    test_rule("2", optional(AnyCharacter))

    test_rule('"A" | "B"', concatenation(
        Terminal, Whitespace, match_string("|"), Whitespace, Terminal))

    test_rule("Identifier = 'something';", Rule)
    test_rule("Identifier = 'something' | something_else | ['ayy'];", Rule)
    test_rule("Identifier = ('thing1' | 'thing2') | 'something' | something_else | ['ayy'] | { [ident ] };", Rule)
    test_rule("Identifier = ('thing1' | 'thing2'), else | 'something' | something_else | ['ayy'] | { [ident ] };", Rule)

    test_rule('letter = "A" | "B" | "C" | "D" | "E" | "F" | "G" | "H" | "I" | "J" | "K" | "L" | "M" | "N" | "O" | "P" | "Q" | "R" | "S" | "T" | "U" | "V" | "W" | "X" | "Y" | "Z" | "a" | "b" | "c" | "d" | "e" | "f" | "g" | "h" | "i" | "j" | "k" | "l" | "m" | "n" | "o" | "p" | "q" | "r" | "s" | "t" | "u" | "v" | "w" | "x" | "y" | "z" ;', Grammar)

    test_rule("""
letter = "A" | "B" | "C" | "D" | "E" | "F" | "G"
       | "H" | "I" | "J" | "K" | "L" | "M" | "N"
       | "O" | "P" | "Q" | "R" | "S" | "T" | "U"
       | "V" | "W" | "X" | "Y" | "Z" | "a" | "b"
       | "c" | "d" | "e" | "f" | "g" | "h" | "i"
       | "j" | "k" | "l" | "m" | "n" | "o" | "p"
       | "q" | "r" | "s" | "t" | "u" | "v" | "w"
       | "x" | "y" | "z" ;
digit = "0" | "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9" ;
symbol = "[" | "]" | "{" | "}" | "(" | ")" | "<" | ">"
       | "'" | '"' | "=" | "|" | "." | "," | ";" ;
character = letter | digit | symbol | "_" ;

identifier = letter , { letter | digit | "_" } ;
terminal = "'" , character , { character } , "'"
         | '"' , character , { character } , '"' ;

lhs = identifier ;
rhs = identifier
     | terminal
     | "[" , rhs , "]"
     | "{" , rhs , "}"
     | "(" ,rhs , ")"
     | rhs , "|" , rhs
     | rhs , "," , rhs ;

rule = lhs , "=" , rhs , ";" ;
grammar = { rule } ;
              """, Grammar)

    return 0


if __name__ == "__main__":
    main()


