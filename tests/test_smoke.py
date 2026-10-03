from acfpf import __version__
from acfpf.source_registry import load_sources


def test_version_is_defined() -> None:
    assert __version__


def test_source_registry_loads() -> None:
    sources = load_sources()
    assert sources
    assert any(source.id == "insee" for source in sources)
