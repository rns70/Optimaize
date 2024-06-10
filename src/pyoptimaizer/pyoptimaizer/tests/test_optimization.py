from pathlib import Path
import pyoptimaizer.tests
from pyoptimaizer.optimize import cythonize_function
import pytest

example_code_dir_path = Path(pyoptimaizer.tests.__file__).parent / "example_code"


ALL_EXAMPLES = [x.stem for x in example_code_dir_path.iterdir() if x.is_file() and x.suffix == ".py"]

def format_example(name):
    example_path = str(example_code_dir_path / f"{name}.py")
    return example_path + "::" + name

@pytest.mark.parametrize("name", [x for x in ALL_EXAMPLES])
def test_optimize_function(name):
    example = format_example(name)
    cythonize_function(example)
    assert True