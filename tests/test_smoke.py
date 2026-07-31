import choreoai


def test_version_is_present():
    assert isinstance(choreoai.__version__, str)
    assert choreoai.__version__
