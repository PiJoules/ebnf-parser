# -*- coding: utf-8 -*-

from utils import SlotDefinedClass

import itertools
import collections


class StreamHandler(SlotDefinedClass):
    """Class for handling iterating through a stream of characters."""
    __types__ = (str, int, int)
    __slots__ = ("char", "line_no", "col_no", "char_iter", "end", "pos")

    def __init__(self, char_iter, line_no=1, col_no=1, end=None, pos=0):
        self.char_iter = char_iter
        self.line_no = line_no
        self.col_no = col_no
        self.end = end
        self.pos = pos
        self.__pop_without_increment()

    def __pop_without_increment(self):
        if self.end is not None:
            self.pos += 1
            if self.pos >= self.end:
                self.char = ""
                return
        self.char = next(self.char_iter, "")

    def pop_char(self):
        """Get the next character and increment the location."""
        if self.char:
            if self.char == "\n":
                self.line_no += 1
                self.col_no = 1
            else:
                self.col_no += 1
            self.__pop_without_increment()

    def __copy_iter(self):
        self.char_iter, copied_iter = itertools.tee(self.char_iter)
        return copied_iter

    def __deepcopy__(self, memo):
        """
        Create a copy of the handler such that advancing this iterator
        will not advance the copied iterator.
        Since the potential iterator could be for a generator, which cannot
        be copied, the implementation of this varies based on where the stream
        comes from.
        """
        #raise NotImplementedError
        copied_iter = self.__copy_iter()
        handler = StreamHandler(itertools.chain([self.char], copied_iter),
                                line_no=self.line_no,
                                col_no=self.col_no,
                                end=self.end,
                                pos=self.pos)
        return handler

    def update(self, handler):
        """Update the properties of this handler to match those of another."""
        super(StreamHandler, self).update(**handler.json())

    def __str__(self):
        return str(self.json())

    def advance(self, n):
        for i in xrange(n):
            self.pop_char()


def partition_stream_handler(handler, n):
    def partitions(handler, *args):
        if not args:
            return []

        first_part = copy.deepcopy(handler)

        if len(args) == 1 or not first_part.char:
            return [first_part]

        # Create 1st partition of size
        copied_handler = copy.deepcopy(first_part)
        size = args[0]
        first_part.end = size

        # Advance remaining
        copied_handler.advance(size)

        # copied_handler is now the rest of the stream
        return [first_part] + partitions(copied_handler, *args[1:])

    for nums in sum_to_n(len(lst), n):
        yield partitions()





def partition_list(lst, n):
    for nums in sum_to_n(len(lst), n):
        start = 0
        parts = []
        for num in nums:
            end = start + num
            parts.append(lst[start:end])
            start = end
        yield parts


