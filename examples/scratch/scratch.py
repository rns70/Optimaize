from pathlib import Path
from pyoptimaizer.optimize import run_test_file_with_replacement_function
import sys

sys.path.append('toy_project/toy_project')

run_test_file_with_replacement_function(
    test_file_path=Path('toy_project/toy_project/test_fibonacci.py'),
    function_name='fibonacci',
    replacement_function_path=Path('toy_project/toy_project/fibonacci.py'),
)

run_test_file_with_replacement_function(
    test_file_path=Path('toy_project/toy_project/test_fibonacci.py'),
    function_name='fibonacci',
    replacement_function_path=Path('toy_project/toy_project/fibonacci_optimized.pyx'),
)