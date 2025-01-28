def test_version_availability():
    from src.chewdoc import __version__
    assert isinstance(__version__, str)
    assert len(__version__.split('.')) >= 3 