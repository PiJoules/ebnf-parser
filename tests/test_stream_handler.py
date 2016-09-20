#!/usr/bin/env python
# -*- coding: utf-8 -*-

from parser_gen.utils import char_generator
from parser_gen.stream_handler import StreamHandler
from parser_gen.iterator_tools import ExtendedIterator

import unittest
import copy


TEST_GRAMMAR = "ebnf_grammar.txt"


class TestStreamHandler(unittest.TestCase):
    def setUp(self):
        self.handler = StreamHandler(ExtendedIterator(char_generator(TEST_GRAMMAR)))

    def test_iteration(self):
        """Test normal iteration through the handler."""
        gen = char_generator(TEST_GRAMMAR)

        for c in gen:
            self.handler.pop_char()
            self.assertEqual(c, self.handler.char())

        self.handler.pop_char()
        self.assertEqual(self.handler.char(), "")

    def __advance_stream(self, handler, n=10):
        handler.advance(n)

    def test_copy(self):
        """Test that a copied handler has a completely different stream."""
        self.__advance_stream(self.handler)
        copied_handler = copy.deepcopy(self.handler)
        self.__advance_stream(self.handler)
        self.__advance_stream(copied_handler)

        for i in xrange(10):
            self.assertEqual(self.handler.char(), copied_handler.char())
            self.handler.pop_char()
            copied_handler.pop_char()

    def test_no_partitions(self):
        handler = StreamHandler(ExtendedIterator(iter("")))
        parts = list(handler.partitions(3))
        self.assertFalse(parts)


if __name__ == "__main__":
    unittest.main()

