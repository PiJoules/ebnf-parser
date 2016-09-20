# -*- coding: utf-8 -*-

def peek_stream(stream, n):
    top = stream.peek_n(n)
    return top + [""] * (n - len(top))


def table_parse(stream, starting_rule, k=1):
    stack = [starting_rule()]
    head = stack[-1]

    while stack:
        top_rule = stack.pop()
        lookaheads = peek_stream(stream, k)

        if top_rule == lookaheads[0]:
            stream.pop_char()
        else:
            rules = top_rule.get_rules(*lookaheads)
            if rules is not None:
                rules = tuple(r() for r in rules)
                top_rule.apply_rules(rules)
                stack += list(reversed(rules))
            else:
                raise RuntimeError("Unable to handle token '{}' for rule '{}'. {}".format(lookaheads[0], type(top_rule).__name__, stream))

    if stack:
        raise RuntimeError("Stack was not exhausted: {}".format([type(x).__name__ for x in stack]))

    return head

