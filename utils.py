#-*- coding: utf-8 -*-

import string
import logging
import sys


def base_parse_args(parser, name=None):
    """Add various arguments for more verbosity."""

    # Logging/debugging
    parser.add_argument("-v", "--verbose", action="count", default=0,
                        help="Logging verbosity. More verbose means more "
                        "logging info.")

    args = parser.parse_args()

    # Configure logger
    logging.basicConfig(format="[%(asctime)s] %(levelname)s: %(message)s",
                        stream=sys.stderr)
    if name:
        logger = logging.getLogger(name)
        if args.verbose == 1:
            logger.setLevel(logging.INFO)
        elif args.verbose == 2:
            logger.setLevel(logging.DEBUG)

    return args


def contains_chars(s, chars):
    """Checks is a string contains any character in a list of chars."""
    return any((c in chars) for c in s)


def contains_whitespace(s):
    """Check if a string contains whitespace."""
    return contains_chars(s, string.whitespace)


def check_type(v, t):
    assert isinstance(v, t), "Expected '{}' to be of type '{}'. Found type '{}'".format(v, t, type(v))


def check_list(lst, t):
    check_type(lst, list)
    for v in lst:
        check_type(v, t)


def check_dict(d, key_type, val_type):
    check_type(d, dict)
    keys = d.keys()
    vals = d.values()
    check_list(keys, key_type)
    check_list(vals, val_type)


class SlotDefinedClass(object):
    # Type names.
    # Only checks upper most type (i.e. can determine type of variable
    # to be a list, but cannot make assertions regarding the types of the
    # list contents.
    __slots__ = ()

    # Expected type for each slot
    __types__ = ()

    TYPE_MEMBER = "__cls__"

    def __init__(self, **kwargs):
        self.update(**kwargs)

    def update(self, **kwargs):
        types = self.__types__
        for i, attr in enumerate(self.__slots__):
            v = kwargs[attr]
            if i < len(types):
                t = types[i]
                if isinstance(t, list):
                    check_list(v, t[0])
                elif isinstance(t, dict):
                    check_dict(v, t.keys()[0], v.values()[0])
                else:
                    # Check that this property is of the specified type
                    check_type(v, t)
            setattr(self, attr, v)

    def dict(self):
        """Return a shallow dictionary representation of this instance for easy kwargs unpacking."""
        return {k: getattr(self, k) for k in self.__slots__}

    def json(self):
        """Produce a json serializeable version of instances of this class."""
        assert getattr(self, self.TYPE_MEMBER, None) is None
        d = {self.TYPE_MEMBER: type(self).__name__}
        for k in self.__slots__:
            v = getattr(self, k)
            if isinstance(v, SlotDefinedClass):
                d[k] = v.json()
            elif isinstance(v, (list, tuple)):
                d[k] = tuple(x.json() if isinstance(x, SlotDefinedClass) else x for x in v)
            else:
                d[k] = v
        return d

    def __eq__(self, other):
        """Just check the type and each of the attributes."""
        if not isinstance(self, type(other)):
            return False
        return all(getattr(self, attr) == getattr(other, attr) for attr in self.__slots__)

    def __ne__(self, other):
        return not (self == other)
