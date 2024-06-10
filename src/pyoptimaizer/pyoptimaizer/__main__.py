import argparse
import sys
from pyoptimaizer.optimize import cythonize_function
# Desc: Main file for python_optimaizer


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    # pythom -m optimaizer /path/to/file::function_name /path_to_test_1::function_name /path_to_test_2::function_name ...
    parser.add_argument('function_to_optimize', type=str, help='Path to file with function')
    parser.add_argument('test_functions', type=str, nargs='+', help='Path to file with test functions')
    # openai url
    parser.add_argument('--openai_url', type=str, default='https://api.openai.com/v1/engines/davinci/completions', help='Openai url')
    args = parser.parse_args(sys.argv[1:])
    
    function_to_optimize = args.function_to_optimize
    test_functions = args.test_functions if len(args.test_functions)>0 else []
    print(f"Optimizing function: {function_to_optimize}", f"Test functions: {test_functions}")
    cythonize_function(function_to_optimize, test_functions)