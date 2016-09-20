#!/usr/bin/env python
# -*- coding: utf-8 -*-

from parser_gen.stream_handler import *
from parser_gen.production_rules import *
from parser_gen.parse import *

import unittest


class TestRules(unittest.TestCase):
    def __make_prod(self, s, rule_cls):
        return table_parse(StreamHandler.from_str(s), rule_cls)

    def __test_rule_str(self, s, rule_cls):
        prod = self.__make_prod(s, rule_cls)
        self.assertEqual(s, str(prod))

    def __test_rule_json(self, s, rule_cls, expect):
        prod = self.__make_prod(s, rule_cls)
        self.assertEqual(prod.json(), expect)

    def __test_rule(self, s, rule_cls, json=None):
        prod = self.__make_prod(s, rule_cls)
        self.assertEqual(s, str(prod))
        if json:
            self.assertEqual(prod.json(), json)

    def test_letter(self):
        self.__test_rule("A", Letter, "A")

    def test_digit(self):
        self.__test_rule("9", Digit, "9")

    def test_rest(self):
        """These need to be sorted into their own test methods."""
        self.__test_rule("]", Symbol, json="]")
        self.__test_rule("abc", terminal("abc"), json="abc")
        self.__test_rule("", terminal(""), json="")
        self.__test_rule("ABCD", Identifier, json={
            "Identifier": [
                "A",
                ["B", "C", "D"]
            ]
        })
        self.__test_rule("ABC", repetition(Letter), json=["A", "B", "C"])
        self.__test_rule("", repetition(Letter), json=[])
        self.__test_rule("A", alternation(Letter, Digit, Symbol), json="A")
        self.__test_rule("9", alternation(Letter, Digit, Symbol), json="9")
        self.__test_rule(")", alternation(Letter, Digit, Symbol), json=")")
        self.__test_rule(")89dfg", repetition(alternation(Letter, Digit, Symbol)), json=
            [")", "8", "9", "d", "f", "g"]
        )
        self.__test_rule("a", exclusion(AnyCharacter, terminal("b")), json="a")
        self.__test_rule("fkshff", repetition(exclusion(AnyCharacter, terminal("'"))), json=[
            "f", "k", "s", "h", "f", "f"
        ])
        self.__test_rule("''", Terminal, json={
            "Terminal": ["'", [], "'"]
        })
        self.__test_rule("\\s", EscapeCharacter, json={
            "EscapeCharacter": ["\\", "s"]
        })
        self.__test_rule("'\\''", Terminal, json={
            "Terminal": [
                "'",
                [{
                    "EscapeCharacter": ["\\", "'"]
                }],
                "'"
            ]
        })
        self.__test_rule("'some string'", Terminal, json={
            "Terminal": ["'", list("some string"), "'"]
        })
        self.__test_rule("'some \\string'", Terminal, json={
            "Terminal": ["'", list("some ") + [{"EscapeCharacter": ["\\", "s"]}] + list("tring"), "'"]
        })
        self.__test_rule('"\\""', Terminal, json={
            "Terminal": [
                '"',
                [{
                    "EscapeCharacter": ["\\", '"']
                }],
                '"'
            ]
        })
        self.__test_rule('"some string"', Terminal, json={
            "Terminal": ['"', list("some string"), '"']
        })
        self.__test_rule('"some \\string"', Terminal, json={
            "Terminal": ['"', list("some ") + [{"EscapeCharacter": ["\\", "s"]}] + list("tring"), '"']
        })
        self.__test_rule("", optional(Digit), json="")
        self.__test_rule("2", optional(Digit), json="2")
        self.__test_rule(" ", SingleWhitespace, json=" ")
        self.__test_rule("\n", SingleWhitespace, json="\n")
        self.__test_rule("     ", Whitespace, json="     ")
        self.__test_rule("ab", concatenation(Letter, Letter), json=["a", "b"])
        self.__test_rule("abc9_", concatenation(Letter, repetition(alternation(Letter, Digit, terminal("_")))), json=[
            "a", ["b", "c", "9", "_"]
        ])

        self.__test_rule("ident", SingleProduction, json={
            "SingleProduction": [self.__make_prod("ident", Identifier).json()]
        })
        self.__test_rule("ident", Alternation, json={
            "Alternation": [self.__make_prod("ident", Concatenation).json(), "", []]
        })

        self.__test_rule("ident | ident2 | ident3", Alternation, json={
            "Alternation": [
                self.__make_prod("ident ", Concatenation).json(),
                "",
                [
                    {
                        "MaybeAlternation": [
                            "|",
                            " ",
                            self.__make_prod("ident2 ", Concatenation).json(),
                        ]
                    },
                    {
                        "MaybeAlternation": [
                            "|",
                            " ",
                            self.__make_prod("ident3", Concatenation).json(),
                        ]
                    }
                ]
            ]
        })
        self.__test_rule("'term'", SingleProduction, json={
            "SingleProduction": [self.__make_prod("'term'", Terminal).json()]
        })


        self.__test_rule("[a]b", concatenation(Optional, Letter), json=[
            self.__make_prod("[a]", Optional).json(),
            "b"
        ])
        self.__test_rule("[a], b", Alternation, json={
            "Alternation": [
                self.__make_prod("[a], b", Concatenation).json(),
                "",
                []
            ]
        })

        self.__test_rule("{a}b", concatenation(Repetition, Letter))

        self.__test_rule("a | b | c", Alternation)
        self.__test_rule("a = b;", Rule)
        self.__test_rule("a = b;", Grammar)

        test = """letter = "A" | "B" | "C" | "D" | "E" | "F" | "G"
        | "H" | "I" | "J" | "K" | "L" | "M" | "N"
        | "O" | "P" | "Q" | "R" | "S" | "T" | "U"
        | "V" | "W" | "X" | "Y" | "Z" | "a" | "b"
        | "c" | "d" | "e" | "f" | "g" | "h" | "i"
        | "j" | "k" | "l" | "m" | "n" | "o" | "p"
        | "q" | "r" | "s" | "t" | "u" | "v" | "w"
        | "x" | "y" | "z" ;
                """
        self.__test_rule(test, Grammar)

        test = """letter = "A" | "B" | "C" | "D" | "E" | "F" | "G"
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
                """
        self.__test_rule(test, Grammar)


if __name__ == "__main__":
    unittest.main()

