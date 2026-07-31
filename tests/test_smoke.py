import choreo


def test_version_is_present():
    assert isinstance(choreo.__version__, str)
    assert choreo.__version__
