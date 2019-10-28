import copy
import pathlib

import more_itertools


def process(app, stream):
    head, stream = more_itertools.spy(stream)

    # Latest episode must be the welcome page. We've got to think how to
    # make this rule declarative and set it in .holocron.yml.
    first = copy.deepcopy(head[0])
    first["source"] = pathlib.Path("welcome://")
    first["destination"] = pathlib.Path("index.html")
    yield first

    yield from stream
