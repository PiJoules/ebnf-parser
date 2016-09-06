#-*- coding: utf-8 -*-

from production_rule import *


TEST_STRING = """
"""


class Identifier(ProductionRule):
    def _parse(self):
        pass


def main():
    letter = Letter.from_str(TEST_STRING)
    return 0


if __name__ == "__main__":
    main()

