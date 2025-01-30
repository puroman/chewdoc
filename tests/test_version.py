def test_version_availability():
    from src.chewed import __version__

    assert isinstance(__version__, str)
    assert len(__version__.split(".")) >= 3
