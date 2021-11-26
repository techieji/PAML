from paml import import_module
import pytest

@pytest.mark.parametrize("filename", [f'test{n}.paml' for x in range(1, 5)])
def test_file(filename):
    import_module(filename)