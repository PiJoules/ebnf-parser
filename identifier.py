#-*- coding: utf-8 -*-

from __future__ import print_function

from production_rule import *
from letter import Letter


TEST_STRING = "AAA_9_"


class Digit(ProductionRule):
    def parse(self):
        char = self._pop_char()
        if not char.isdigit():
            self._raise_syntax_error(expected="alphabetic character")
        self._set_productions(char)


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


class Identifier(ProductionRule):
    def parse(self):
        productions = []

        # letter, { letter | digit | _ }, _
        # Concatentation
        for parts in self.stream_handler().partitions(3):
            try:
                print("first part:", parts[0])
                letter = Letter(parts[0])

                print("second part:", parts[1])

                # repetition
                repetition = []
                while parts[1].char():
                    try:

                        # alternation
                        next_rule = None
                        for rule_cls in (Letter, Digit, match_string("_")):
                            try:
                                copied_handler = copy.deepcopy(parts[1])
                                next_rule = rule_cls(copied_handler)
                            except RuleSyntaxError:
                                pass
                            else:
                                break
                        else:
                            self._raise_syntax_error(expected="letter, digit, or '_'")

                    except RuleSyntaxError:
                        break
                    else:
                        repetition.append(next_rule)
                        parts[1].update_from_handler(copied_handler)


                print("third part:", parts[2])
                underscore = match_string("_")(parts[2])

            except RuleSyntaxError:
                pass
            else:
                productions.append(letter)

                # repetition
                productions += repetition

                productions.append(underscore)

                print("final productions:", map(str, productions))

                self.stream_handler().update_from_handler(parts[-1])
                print("rest:", self.stream_handler())
                break
        else:
            self._raise_syntax_error(expected="letter")

        self._set_productions(productions)


def main():
    identifier = Identifier.from_str(TEST_STRING)
    print(identifier)
    return 0


if __name__ == "__main__":
    main()

