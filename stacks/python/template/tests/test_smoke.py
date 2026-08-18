"""Proof the toolchain and the package import work."""

from __MODULE__ import __version__


def test_version_is_set() -> None:
    assert __version__
