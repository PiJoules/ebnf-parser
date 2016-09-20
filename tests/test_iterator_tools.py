#!/usr/bin/env python
# -*- coding: utf-8 -*-

from parser_gen.iterator_tools import *

import copy
import unittest


ITEMS = 10


class TestIteratorTools(unittest.TestCase):
    def setUp(self):
        self.__iter = ExtendedIterator(xrange(ITEMS))

    def __test_equal_generators(self, base, other):
        for x in base:
            self.assertEqual(x, next(other))

    def test_partitioned_iterator(self):
        self.__iter, parts = partition_iterator(self.__iter, 2, 3)
        self.assertEqual(len(parts), 3)
        for part in parts:
            self.__test_equal_generators(part, self.__iter)

    def test_peek(self):
        elems = self.__iter.peek(ITEMS)
        for i, elem in enumerate(self.__iter):
            self.assertEqual(elem, elems[i])

    def test_peek_empty_stream(self):
        iterator = ExtendedIterator(xrange(0))
        self.assertEqual(iterator.peek(1), [])

        iterator = ExtendedIterator(xrange(1))
        next(iterator)
        self.assertEqual(iterator.peek(1), [])

    def test_deep_copy(self):
        copied = copy.deepcopy(self.__iter)
        self.assertNotEqual(id(self.__iter), id(copied))
        for x in self.__iter:
            self.assertEqual(x, next(copied))

    def test_boolean(self):
        self.assertTrue(self.__iter)
        self.assertFalse(ExtendedIterator(xrange(0)))

    def test_all_iterator_partitions(self):
        x = list(all_iterator_partitions(self.__iter, 3))
        self.assertEqual(36, len(x))


if __name__ == "__main__":
    unittest.main()

