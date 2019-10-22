"""Chain and order stream of items.

This processor is something I wanted to see in Holocron for a long time. I
wasn't sure about its interface and I'm still not sure about it. That's why
I'll start with implementing this processor in this repo first, and once I
have some hands on experience I'll incorporate it the main repo.
"""

import operator

import more_itertools


def process(app, stream, *, order_by=None, direction="asc"):
    if order_by:
        # WARNING: Sorting the stream requires evaluating all items from the
        # stream. This alone sets a requirement that all items must fit into,
        # which may not be achievable in certain cases.
        stream = sorted(
            stream, key=operator.itemgetter(order_by), reverse=direction == "desc"
        )

    for previous, current, next_ in more_itertools.windowed(stream, 3):
        if previous:
            previous["next"] = current
            yield previous

        if current:
            current["previous"] = previous
            current["next"] = next_

        if next_:
            next_["previous"] = current

    if current:
        yield current

    if next_:
        yield next_
