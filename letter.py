#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import print_function

from production_rule import ProductionRule, RuleSyntaxError

import string

TEST_STRING = "A"


class Letter(ProductionRule):
    def parse(self):
        # Get char from buffer
        char = self._pop_char()
        if (not char) or (char not in string.ascii_letters):
            self._raise_syntax_error(expected="alphabetic character")
        self._set_productions(char)


def main():
    letter = Letter.from_str(TEST_STRING)
    print(letter)
    return 0


if __name__ == "__main__":
    main()

