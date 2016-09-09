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


def count_diff(h1, h2):
    return h1.char_iter().count() - h2.char_iter().count()


def concatenation(*args, **kwargs):
    """Decorator for Concatentation class."""
    streams = kwargs.get("streams", [])

    class Concatentation(ProductionRule):
        def parse(self):
            #productions = []
            #copied = copy.deepcopy(self.stream_handler())
            #if len(args) == 1:
            #    # Last one; must pass
            #    productions.append(args[0](copied))
            #    self.stream_handler().update_from_handler(copied)
            #elif not args:
            #    self._raise_syntax_error(message="No rule provided.")
            #else:
            #    pass

            productions = []
            #streams = [copy.deepcopy(self.stream_handler())]
            streams = []
            ref_streams = []
            rules = list(reversed(args))
            valid_rules = []
            last_stream = copy.deepcopy(self.stream_handler())

            while rules:
                print("rules:", rules)
                print("streams:", map(str, streams))
                print("prods:", map(str, productions))

                rule = rules.pop()
                #copied = copy.deepcopy(streams[-1])
                copied = copy.deepcopy(last_stream)
                try:
                    prod = rule(copied)
                except RuleSyntaxError:
                    if valid_rules:
                        productions.pop()

                        streams[-1].char_iter().set_end(streams[-1].char_iter().end() - 1)
                        last_stream = streams.pop()

                        rules.append(rule)
                        rules.append(valid_rules.pop())
                    else:
                        print("Failed")
                        self._raise_syntax_error(expected=rule.__name__)
                else:
                    # Success
                    productions.append(prod)

                    ref_streams.append(copy.deepcopy(last_stream))

                    #n = count_diff(copied, streams[-1])
                    n = count_diff(copied, last_stream)
                    #streams[-1].char_iter().set_end(streams[-1].char_iter().count() + n)
                    last_stream.char_iter().set_end(last_stream.char_iter().count() + n)
                    #streams.append(copied)
                    streams.append(last_stream)

                    valid_rules.append(rule)

                    last_stream = copied

            self.stream_handler().update_from_handler(last_stream)
            print("prods:", map(str, productions))

            #copied = copy.deepcopy(self.stream_handler())
            #prod = args[0](copied)
            #n = count_diff(copied, self.stream_handler())
            #streams.append(self.stream_handler().up_to(n))
            #productions.append(prod)

            #i = 1
            #while i < len(args):
            #    backup = copy.deepcopy(copied)
            #    try:
            #        prod = args[i](backup)
            #    except RuleSyntaxError:
            #        # Backtrack to previous prod, limiting the stream
            #    else:
            #        productions.append(prod)
            #        streams.append(copied.up_to(count_diff(backup, copied)))
            #        copied.update_from_handler(backup)


            #    i += 1

            #last_size = -1
            #num_partitions = len(args)
            #last_good_stream = None
            #for parts in self.stream_handler().partitions(num_partitions):
            #    err_count = 0
            #    test_productions = []

            #    # Apply partitions to each rule
            #    for i in xrange(num_partitions):
            #        try:
            #            rule = args[i](parts[i])

            #            # Whole stream must be finished
            #            if parts[i]:
            #                err_count += 1
            #        except RuleSyntaxError:
            #            err_count += 1
            #        else:
            #            test_productions.append(rule)

            #    # Record all valid rules and exit when not able to apply any
            #    # partitions on any rule
            #    if not err_count:
            #        size = len("".join(map(str, test_productions)))
            #        if size > last_size:
            #            last_good_stream = parts[-1]
            #            productions = test_productions
            #            last_size = size
            #    elif err_count >= num_partitions:
            #        # All failed
            #        break

            #if last_good_stream is None:
            #    self._raise_syntax_error(expected="concatenation of {}".format(args))

            #self.stream_handler().update_from_handler(last_good_stream)
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
        overall = concatenation(
                #concatenation(match_string("A"), repetition(match_string("B"))),
                #concatenation(match_string("C"))
                Identifier,
                match_string("_")
            )(self.stream_handler())
        self._set_productions([overall])


def main():
    #test_rule("A", Letter)
    #test_rule("9", Digit)
    #test_rule("literal", match_string("literal"))
    #test_rule("AAA_9__9", Identifier)
    test_rule("'something'", Terminal)
    #test_rule("ABBBC_", Something)

    return 0


if __name__ == "__main__":
    main()


