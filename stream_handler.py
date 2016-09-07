# -*- coding: utf-8 -*-

from utils import SlotDefinedClass


class StreamHandler(object):
    """Class for handling iterating through a stream of characters."""

    def __init__(self, char_iter, line_no=1, col_no=1):
        self.__char_iter = char_iter
        self.__line_no = line_no
        self.__col_no = col_no
        self.__char = ""

    def char(self):
        return self.__char

    def __pop_without_increment(self):
        self.__char = next(self.__char_iter, "")

    def pop_char(self):
        """Get the next character and increment the location."""
        if self.__char == "\n":
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
