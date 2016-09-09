# -*- coding: utf-8 -*-

from utils import SlotDefinedClass
from iterator_tools import ExtendedIterator, all_iterator_partitions, copy_iterator, sum_to_n

import itertools
import copy


class StreamHandler(object):
    """Class for handling iterating through a stream of characters."""

    def __init__(self, char_iter, line_no=1, col_no=1, starting_char=""):
        assert isinstance(char_iter, ExtendedIterator), "The iterator provided to StreamHandler must be an ExtendedIterator."
        self.__char_iter = char_iter
        self.__line_no = line_no
        self.__col_no = col_no
        self.__char = starting_char

    def char(self):
        return self.__char

    def line_no(self):
        return self.__line_no

    def col_no(self):
        return self.__col_no

    def char_iter(self):
        return self.__char_iter

    def __pop_without_increment(self):
        self.__char = next(self.__char_iter, "")

    def pop_char(self):
        """Get the next character and increment the location."""
        char = self.__char
        if char == "\n":
            self.__line_no += 1
            self.__col_no = 1
        elif char:
            self.__col_no += 1
        self.__pop_without_increment()

    def advance(self, n):
        for i in xrange(n):
            self.pop_char()

    def __deepcopy__(self, memo):
        """
        Create a copy of the handler such that advancing this iterator
        will not advance the copied iterator.
        Since the potential iterator could be for a generator, which cannot
        be copied, the implementation of this varies based on where the stream
        comes from.
        """
        handler = StreamHandler(copy.deepcopy(self.__char_iter),
                                line_no=self.__line_no,
                                col_no=self.__col_no,
                                starting_char=self.__char)
        return handler

    def update(self, **kwargs):
        """Update the properties of this handler to match those of another."""
        self.__char_iter = kwargs.get("char_iter", self.__char_iter)
        self.__char = kwargs.get("starting_char", self.__char)
        self.__line_no = kwargs.get("line_no", self.__line_no)
        self.__col_no = kwargs.get("col_no", self.__col_no)

    def update_from_handler(self, handler):
        self.update(char_iter=handler.char_iter(),
                    starting_char=handler.char(),
                    line_no=handler.line_no(),
                    col_no=handler.col_no())

    def __str__(self):
        return "<{} line_no={} col_no={} char='{}' char_iter={}>".format(
            type(self).__name__,
            self.__line_no,
            self.__col_no,
            self.__char,
            self.__char_iter
        )

    def __nonzero__(self):
        return bool(self.__char_iter)

    def partitions(self, partitions):
        n = partitions-1
        if n <= 0:
            yield [copy.deepcopy(self)]
            return
        while True:
            for sizes in sum_to_n(n, size=partitions-1):
                parts = [copy.deepcopy(self)]
                end = 0
                for size in sizes:
                    end += size
                    parts[-1].char_iter().set_end(end)
                    part = copy.deepcopy(parts[-1])
                    part.char_iter().set_end(self.__char_iter.end())
                    part.advance(size)
                    parts.append(part)
                if not all(parts):
                    return
                yield parts
            n += 1

    def pos(self):
        return self.__char_iter.count()

    def peek(self, n=1):
        return self.__char_iter.peek(n)

    def up_to(self, i):
        copied = copy.deepcopy(self)
        new_end = copied.char_iter().count() + i
        if new_end < copied.char_iter().end():
            copied.char_iter().set_end(new_end)
        return copied

    def split_at(self, i):
        copied = copy.deepcopy(self)
        second_copy = copy.deepcopy(self)
        copied.char_iter().set_end(i)
        second_copy.advance(i)
        return copied, second_copy

