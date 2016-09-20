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


def peek_stream(stream, n):
    top = stream.peek_n(n)
    return top + [""] * (n - len(top))


def table_parse(stream, starting_rule):
    stack = [starting_rule()]
    head = stack[-1]

    while stack:
        top_rule = stack.pop()
        lookaheads = peek_stream(stream, K)

        if top_rule == lookaheads[0]:
            stream.pop_char()
        else:
            rules = top_rule.get_rules(*lookaheads)
            if rules is not None:
                rules = tuple(r() for r in rules)
                top_rule.apply_rules(rules)
                stack += list(reversed(rules))
            else:
                raise RuntimeError("Unable to handle token '{}' for rule '{}'. {}".format(lookaheads[0], type(top_rule).__name__, stream))

    if stack:
        raise RuntimeError("Stack was not exhausted: {}".format([type(x).__name__ for x in stack]))

    return head


def quick_prod(s, rule_cls):
    return table_parse(StreamHandler.from_str(s), rule_cls)


def test_rule(s, rule_cls, json=None, expect=None):
    expect = expect or s
    prod = quick_prod(s, rule_cls)
    assert expect == str(prod), "Expected \"{}\". Found \"{}\".".format(expect, prod)
    if json:
        import json as json_mod
        assert prod.json() == json, "Expected \n{}\nFound\n{}".format(
            #json, prod.json()
            json_mod.dumps(json, indent=4),
            json_mod.dumps(prod.json(), indent=4)
        )


def print_rule(s, rule_cls):
    prod = quick_prod(s, rule_cls)
    print(json.dumps(prod.json(), indent=4))


def main():
    test_rule("A", Letter, json="A")
    test_rule("9", Digit, json="9")
    test_rule("]", Symbol, json="]")
    test_rule("abc", terminal("abc"), json="abc")
    test_rule("", terminal(""), json="")
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
    test_rule("a", exclusion(AnyCharacter, terminal("b")), json="a")
    test_rule("fkshff", repetition(exclusion(AnyCharacter, terminal("'"))), json=[
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
    test_rule(" ", SingleWhitespace, json=" ")
    test_rule("\n", SingleWhitespace, json="\n")
    test_rule("     ", Whitespace, json="     ")
    test_rule("ab", concatenation(Letter, Letter), json=["a", "b"])
    test_rule("abc9_", concatenation(Letter, repetition(alternation(Letter, Digit, terminal("_")))), json=[
        "a", ["b", "c", "9", "_"]
    ])

    test_rule("ident", SingleProduction, json={
        "SingleProduction": [quick_prod("ident", Identifier).json()]
    })
    test_rule("ident", Alternation, json={
        "Alternation": [quick_prod("ident", Concatenation).json(), "", []]
    })

    test_rule("ident | ident2 | ident3", Alternation, json={
        "Alternation": [
            quick_prod("ident ", Concatenation).json(),
            "",
            [
                {
                    "MaybeAlternation": [
                        "|",
                        " ",
                        quick_prod("ident2 ", Concatenation).json(),
                    ]
                },
                {
                    "MaybeAlternation": [
                        "|",
                        " ",
                        quick_prod("ident3", Concatenation).json(),
                    ]
                }
            ]
        ]
    })
    test_rule("'term'", SingleProduction, json={
        "SingleProduction": [quick_prod("'term'", Terminal).json()]
    })


    test_rule("[a]b", concatenation(Optional, Letter), json=[
        quick_prod("[a]", Optional).json(),
        "b"
    ])
    test_rule("[a], b", Alternation, json={
        "Alternation": [
            quick_prod("[a], b", Concatenation).json(),
            "",
            []
        ]
    })

    test_rule("{a}b", concatenation(Repetition, Letter))

    test_rule("a | b | c", Alternation)
    test_rule("a = b;", Rule)
    test_rule("a = b;", Grammar)

    test = """letter = "A" | "B" | "C" | "D" | "E" | "F" | "G"
       | "H" | "I" | "J" | "K" | "L" | "M" | "N"
       | "O" | "P" | "Q" | "R" | "S" | "T" | "U"
       | "V" | "W" | "X" | "Y" | "Z" | "a" | "b"
       | "c" | "d" | "e" | "f" | "g" | "h" | "i"
       | "j" | "k" | "l" | "m" | "n" | "o" | "p"
       | "q" | "r" | "s" | "t" | "u" | "v" | "w"
       | "x" | "y" | "z" ;
              """
    test_rule(test, Grammar)

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
    test_rule(test, Grammar)

    # Fails on alternation of repetitions
    #test_rule("9", alternation(repetition(Letter), repetition(Digit), repetition(Symbol)))

    return 0


if __name__ == "__main__":
    main()

