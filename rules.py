#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

from production_rule import *

import string
import copy
import json
import sys

sys.setrecursionlimit(1000000)


class Letter(ProductionRule):
    def parse(self):
        # Get char from buffer
        char = self.pop_char()
        if (not char) or (char not in string.ascii_letters):
            self._raise_syntax_error(expected="alphabetic character")
        return char


class Symbol(ProductionRule):
    SYMBOLS = "[]{}()<>'\"=|.,;"

    def parse(self):
        # Get char from buffer
        char = self.pop_char()
        if (not char) or (char not in self.SYMBOLS):
            self._raise_syntax_error(expected="one of the characters '{}'".format(self.SYMBOLS))
        return char


class Digit(ProductionRule):
    def parse(self):
        char = self.pop_char()
        if not char.isdigit():
            self._raise_syntax_error(expected="alphabetic character")
        return char


class Terminal(ProductionRule):
    def parse(self):
        # "'", { character }, "'"
        # '"', { character }, '"'
        return [
            alternation(
                concatenation(
                    terminal_string("'"),
                    repetition(exclusion(AnyCharacter, terminal_string("'"))),
                    terminal_string("'")
                ),
                concatenation(
                    terminal_string('"'),
                    repetition(exclusion(AnyCharacter, terminal_string('"'))),
                    terminal_string('"')
                )
            )(self.stream_handler())
        ]


class Identifier(ProductionRule):
    def parse(self):
        # Letter, { Letter, Digit, "_" }
        alt = alternation(Letter, Digit, terminal_string("_"))
        rep = repetition(alt)
        return [concatenation(Letter, rep)(self.stream_handler())]

    def json(self):
        return {
            type(self).__name__: str(self)
        }


class Optional(ProductionRule):
    def parse(self):
        return [
            concatenation(
                terminal_string("["),
                Whitespace,
                Productions,
                Whitespace,
                terminal_string("]")
            )(self.stream_handler())
        ]


class Repetition(ProductionRule):
    def parse(self):
        return [
            concatenation(
                terminal_string("{"),
                Whitespace,
                Productions,
                Whitespace,
                terminal_string("}"),
            )(self.stream_handler())
        ]


class Grouping(ProductionRule):
    def parse(self):
        return [
            concatenation(
                terminal_string("("),
                Whitespace,
                Productions,
                Whitespace,
                terminal_string(")")
            )(self.stream_handler())
        ]


class SingleRule(ProductionRule):
    def parse(self):
        return [
            alternation(
                Identifier,
                Terminal,
                Optional,
                Repetition,
                Grouping,
            )(self.stream_handler())
        ]


class Concatentation(ProductionRule):
    def parse(self):
        return [
            alternation(
                concatenation(
                    SingleRule,
                    Whitespace,
                    terminal_string(","),
                    Whitespace,
                    Concatentation
                ),
                SingleRule
            )(self.stream_handler())
        ]


class Alternation(ProductionRule):
    def parse(self):
        return [
            alternation(
                concatenation(
                    Concatentation,
                    Whitespace,
                    terminal_string("|"),
                    Whitespace,
                    Alternation
                ),
                Concatentation
            )(self.stream_handler())
        ]


class Productions(ProductionRule):
    def parse(self):
        x = [Alternation(self.stream_handler())]
        return x


class Rule(ProductionRule):
    def parse(self):
        return [
            concatenation(
                Identifier,
                Whitespace,
                terminal_string("="),
                Whitespace,
                Productions,
                Whitespace,
                terminal_string(";"),
                Whitespace
            )(self.stream_handler())
        ]


class Grammar(ProductionRule):
    def parse(self):
        return [repetition(Rule)(self.stream_handler())]


def test_rule(test, rule_cls):
    test = test.strip()
    x = str(rule_cls.from_str(test))
    assert x == test, "Expected {}, found '{}'.".format(test, x)


def test_rule_json(test, rule_cls, expected_dict):
    test = test.strip()
    x = rule_cls.from_str(test).json()
    assert x == expected_dict, "Expected {}, found {}".format(
        json.dumps(expected_dict, indent=4),
        json.dumps(x, indent=4)
    )


def main():
    test_rule("A", Letter)
    test_rule("9", Digit)
    test_rule("[", Symbol)
    test_rule("literal", terminal_string("literal"))
    test_rule("AAA_9__9", Identifier)
    test_rule("'something'", Terminal)
    test_rule('"something"', Terminal)
    test_rule("   ", Whitespace)
    test_rule("'something' name", concatenation(Terminal, Whitespace, Identifier))
    test_rule("", optional(AnyCharacter))
    test_rule("2", optional(AnyCharacter))

    test_rule('"A" | "B"', concatenation(
        Terminal, Whitespace, terminal_string("|"), Whitespace, Terminal))

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

    #print(json.dumps(Grammar.from_filename("ebnf_grammar.txt").json(), indent=4))
    test_rule_json("A", Letter, {
        "Letter": "A"
    })
    test_rule_json("9", Digit, {
        "Digit": "9"
    })
    test_rule_json("}", Symbol, {
        "Symbol": "}"
    })
    test_rule_json("literal", terminal_string("literal"), {
        "TerminalString": "literal"
    })
    test_rule_json("ABCDEF__9", Identifier, {
        "Identifier": "ABCDEF__9"
    })
    test_rule_json("'something'", Terminal, {
        "Terminal": "'something'"
    })

    return 0


if __name__ == "__main__":
    main()


