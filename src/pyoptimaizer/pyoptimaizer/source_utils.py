import ast
from pathlib import Path
from typing import List, Union, Tuple
from loguru import logger

def get_lines_of_function(
    file_path: Union[str, Path], function_name: str
) -> Tuple[int, int]:
    """
    Get the source code of a function from a file.
    Note: only works for functions defined at the top level of the file.
    """
    file_path = Path(file_path)
    py_file = file_path.read_text()

    function_node = [
        n
        for n in ast.parse(file_path.read_text()).body
        if isinstance(n, ast.FunctionDef) and n.name == function_name
    ]
    if not function_node:
        return 0,0
    function_node = function_node[0]
    start_line, end_line = function_node.lineno, function_node.end_lineno
    return start_line, end_line


def get_source_code_of_function(file_path: Union[str, Path], function_name: str) -> str:
    """
    Get the source code of a function from a file.
    Note: only works for functions defined at the top level of the file.
    """
    start_line, end_line = get_lines_of_function(file_path, function_name)
    py_file = file_path.read_text()
    function_code = "\n".join(py_file.split("\n")[start_line - 1 : end_line])
    return function_code


def get_imports(file_path: Union[str, Path]) -> List[str]:
    """
    Get the imports from a file.
    Note: only works for functions defined at the top level of the file.
    """
    file_path = Path(file_path)
    py_file = file_path.read_text()
    imports = [
        n
        for n in ast.parse(py_file).body
        if isinstance(n, (ast.Import, ast.ImportFrom))
    ]
    imports_list = []
    for i in imports:
        start_line, end_line = i.lineno, i.end_lineno
        imports_list.append("\n".join(py_file.split("\n")[start_line - 1 : end_line]))
    return imports_list
