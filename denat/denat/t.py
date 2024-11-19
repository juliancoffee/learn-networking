from collections.abc import Sequence
from typing import Never, overload


def unreachable(*args, **kwargs) -> Never:
    if args or kwargs:
        raise RuntimeError("this shouldn't be reachable:\n{args=}\n{kwargs=}")
    else:
        raise RuntimeError("this should be reachable")


@overload
def assert_never_seq(rest: Never) -> Never:
    pass


@overload
def assert_never_seq(rest: Sequence[Never]) -> Never:
    pass


def assert_never_seq(rest):
    unreachable(rest)
