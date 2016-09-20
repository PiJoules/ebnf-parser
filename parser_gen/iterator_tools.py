#-*- coding: utf-8 -*-

import itertools
import copy


# Thanks: http://stackoverflow.com/a/2065624
def sum_to_n(n, size=None):
    """Generate the series of +ve integer lists which sum to a +ve integer, n."""
    from operator import sub
    mid = xrange(1, n)
    splits = (d for i in xrange(n) for d in itertools.combinations(mid, i))
    for s in splits:
        combo = map(sub, itertools.chain(s, [n]), itertools.chain([0], s))
        if size is not None:
            if len(combo) == size:
                yield combo
        else:
            yield combo


class ExtendedIterator(object):
    """
    More features for the iterator. The original iterator provided should
    no longer be used.
    """
    def __init__(self, iterator, start=0, end=None):
        assert not isinstance(iterator, ExtendedIterator), "The iterator provided to ExtendedIterator must not be an ExtendedIterator."
        self.__iter = iter(iterator)
        self.__end = end
        self.__count = start

    def __iter__(self):
        return self

    def set_end(self, new_end):
        self.__end = new_end

    def next(self):
        if self.__end is not None:
            if self.__count >= self.__end:
                raise StopIteration

        # Automatically raises StopIteration
        item = next(self.__iter)

        # Increment on successful retrieval
        self.__count += 1

        return item

    def count(self):
        return self.__count

    def end(self):
        return self.__end

    def peek(self, n):
        """Args are same as thos passed to islice."""
        if self.__end:
            n = min(n, self.__end - self.__count)
        items = list(itertools.islice(self.__iter, n))
        self.__iter = itertools.chain(items, self.__iter)
        return items

    def __str__(self):
        head = self.peek(1)
        if head:  # Could be empty list
            head = head[0]
            if self.__end:
                buff = str(self.peek(self.__end - self.__count))
            else:
                buff = "[{}..]".format(head)
        else:
            buff = "[]"
        return "<{} count={} end={} stream={}>".format(
            type(self).__name__,
            self.__count,
            self.__end,
            buff
        )

    def iterator(self):
        return self.__iter

    def __deepcopy__(self, memo):
        self.__iter, copied = copy_iterator(self.__iter)
        return ExtendedIterator(
            copied,
            start=self.__count,
            end=self.__end
        )

    def __nonzero__(self):
        return bool(self.peek(1))


def copy_iterator(iterator, n=2):
    # Avoid invifinte recursion by not having nested ExtendedIterators
    if isinstance(iterator, ExtendedIterator):
        iterator = iterator.iterator()
    results = itertools.tee(iterator, n)
    return results


def consume(iterator, n=None):
    """Advance the iterator n-steps ahead. If n is none, consume entirely."""
    # Use functions that consume iterators at C speed.
    if n is None:
        # feed the entire iterator into a zero-length deque
        collections.deque(iterator, maxlen=0)
    else:
        # advance to the empty slice starting at position n
        next(itertools.islice(iterator, n, n), None)


def partition_iterator(iterator, *args, **kwargs):
    """
    Partition an iterator into limited iterators.

    *args represents the lengths of the finite partitons to create.
    This function returns len(args)+1 partitions where the first len(arg)
    parts are each the respective "sizes" of are the ith arg, and the last
    one is the remainder of the partition.

    The first element in the returned tuple is an iterator identical to the
    one passed to this, but must replace the one passed to this.
    The second element is the list of partitons.
    """
    start = kwargs.get("start", 0)
    replacement, first_part, remaining = copy_iterator(iterator, 3)
    if not args:
        remaining = ExtendedIterator(remaining)
        return replacement, [remaining]

    # Set end to first limited iterator
    size = args[0]
    first_part = ExtendedIterator(first_part, end=size)

    # Advance remaining
    remaining = ExtendedIterator(remaining, start=start)
    consume(remaining, n=size)

    # copied_handler is now the rest of the stream
    rest = partition_iterator(remaining, start=start+size, *args[1:])[1]
    return replacement, [first_part] + rest


def all_iterator_partitions(iterator, n):
    """
    Split an iterator by creating different generators that start and end
    at different points.

    Partition by just setting start and end points for generators on each
    partition. The last one will not have and end. This function does not have
    knowledge of the "length" or end of the iterator.

    Work by creating up to n-1 partitions that are split up among an
    incrementing n-1. For example: to split an iterator into n 4 partitions,
    set the initial size as n-1 to be split into n-1 parts, forming 3 initial
    partitions of size 1, and the fourth the remainder of the iterator
    with the first 3 elements popped off. Next is size 4 with 3 parts,
    so the next 3 will be be of size (2, 1, 1), (1, 2, 1), and (1, 1, 2) with
    the fourth in each sequence being the remainder of the iterator with
    the first 4 elements popped off.
    """
    size = n-1
    if size <= 0:
        yield [copy.deepcopy(iterator)]
        return
    while True:
        for nums in sum_to_n(size, n-1):
            iterator, parts = partition_iterator(iterator, *nums)
            if not all(parts):
                return
            yield parts
        size += 1

