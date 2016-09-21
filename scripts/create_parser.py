#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

from parser_gen.production_rules import Grammar
from parser_gen.parse import table_parse
from parser_gen.utils import base_parse_args
from parser_gen.stream_handler import StreamHandler


def get_args():
    from argparse import ArgumentParser
    parser = ArgumentParser(description="Create a parser for an ebnf grammar.")

    parser.add_argument("grammar", help="File containing ebnf grammar.")

    return base_parse_args(parser, __name__)


def main():
    args = get_args()

    filename = args.grammar
    grammar = table_parse(StreamHandler.from_filename(filename), Grammar)
    print(grammar.json())

    return 0


if __name__ == "__main__":
    main()

