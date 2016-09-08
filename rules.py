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
                self._raise_syntax_error(expected=str(self.__rules))

            self._set_productions([next_rule])
    return Alternation


def repetition(rule):
    """Decorator for Repetition class."""
    class Repetition(ProductionRule):
        def parse(self):
            productions = []

            # Keep testing until run into error
            copied = copy.deepcopy(self.stream_handler())
            while copied:
                try:
                    # alternation
                    next_rule = rule(copied)
                except RuleSyntaxError:
                    break
                else:
                    productions.append(next_rule)

            self.stream_handler().advance(len(productions))
            self._set_productions(productions)
    return Repetition


def concatenation(*args):
    """Decorator for Concatentation class."""
    class Concatentation(ProductionRule):
        def parse(self):
            productions = []

            last_size = -1
            num_partitions = len(args)
            last_good_stream = None
            for parts in self.stream_handler().partitions(num_partitions):
                err_count = 0
                test_productions = []

                # Apply partitions to each rule
                for i in xrange(num_partitions):
                    try:
                        rule = args[i](parts[i])

                        # Whole stream must be finished
                        if parts[i]:
                            err_count += 1
                    except RuleSyntaxError:
                        err_count += 1
                    else:
                        test_productions.append(rule)

                # Record all valid rules and exit when not able to apply any
                # partitions on any rule
                if not err_count:
                    size = len("".join(map(str, test_productions)))
                    if size > last_size:
                        last_good_stream = parts[-1]
                        productions = test_productions
                        last_size = size
                elif err_count >= num_partitions:
                    # All failed
                    break

            if last_good_stream is None:
                self._raise_syntax_error(expected="concatenation of {}".format(args))

            self.stream_handler().update_from_handler(last_good_stream)
            self._set_productions(productions)

    return Concatentation


class Terminal(ProductionRule):
    def parse(self):
        # "'", character, { character }, "'"
        self._set_productions([
            concatenation(
                match_string("'"),
                AnyCharacter,
                repetition(AnyCharacter),
                match_string("'")
            )(self.stream_handler())
        ])


class Identifier(ProductionRule):
    def parse(self):
        # Letter, { Letter, Digit, "_" }
        alt = alternation(Letter, Digit, match_string("_"))
        rep = repetition(alt)
        self._set_productions([concatenation(Letter, rep)(self.stream_handler())])


def test_rule(test, rule_cls):
    x = str(rule_cls.from_str(test))
    assert x == test, "Expected {}, found {}.".format(test, x)


class Something(ProductionRule):
    def parse(self):
        self._set_productions([
            concatenation(
                #concatenation(match_string("A"), repetition(match_string("B"))),
                #concatenation(match_string("C"))
                Identifier,
                match_string("_")
            )(self.stream_handler())
        ])


def main():
    test_rule("A", Letter)
    test_rule("9", Digit)
    test_rule("literal", match_string("literal"))
    test_rule("AAA_9__9", Identifier)
    test_rule("'something'", Terminal)
    test_rule("ABBBBBBBBBC_", Something)

    return 0


if __name__ == "__main__":
    main()


