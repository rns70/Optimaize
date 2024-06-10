import importlib
import importlib.util
from pathlib import Path
import subprocess
import sys
from typing import IO, List, Tuple, Union, cast
from pyoptimaizer.display import display_ordered_runtimes
from pyoptimaizer.exceptions import AllGenerationsFailedError, AllTestFailedError, CythonCompilerError
from pyoptimaizer.html_display import render
from pyoptimaizer.source_utils import get_imports, get_source_code_of_function
from pyoptimaizer.assistants import (
    AssistantCodeOptimizationResult,
    CythonCodeOptimizerAssistant,
    PythonTestCreatorAssistant,
)
from pyoptimaizer.types import EvaluatedOptimizedFunctionResult
from pyoptimaizer.utils import Process, retry
from pyoptimaizer.source_utils import get_lines_of_function
from loguru import logger
from timeit import Timer
from openai.types.chat import ChatCompletionMessage


def get_all_test_functions_in_module(module):
    """Get all functions in a module.
    Args:
        module: Module to get functions from.
    """
    funcs = []
    for name in dir(module):
        attr = getattr(module, name)
        if callable(attr) and name.startswith("test"):
            funcs.append(attr)
    return funcs

class FaultyTestError(Exception):
    def __init__(self, test_name, function):
        self.test_name = test_name
        self.function = function
        super().__init__(f"Error running test {test_name} with {function}")

def run_test_file_with_replacement_function(
    test_file_path, replacement_function_path, function_name
):
    """Run a test file with a cythonized function.
    Args:
        test_file (str): Path to the test file.
        optimized_function_path (str): Path to the optimized function.
        function_name (str): Name of the function to test.
    """
    test_module = import_module_from_file(test_file_path)
    replacement_module = import_module_from_file(replacement_function_path)
    replacement_func = getattr(replacement_module, function_name)
    setattr(test_module, function_name, replacement_func)
    # run tests
    tests = get_all_test_functions_in_module(test_module)
    # benchmark tests
    avg_times = {}
    for test in tests:
        t = Timer(test)
        try:
            num_of_trials, total_time = t.autorange()
        except Exception as e:
            raise FaultyTestError(test.__name__, Path(replacement_function_path).stem) from e
        avg_time = total_time / num_of_trials
        print(f"{test.__name__}: avg {avg_time} (s) over {num_of_trials} trials")
        avg_times[test.__name__] = avg_time

    # TODO: lets return the avg of all tests for now (maybe replace with geometric mean or whatever)
    return sum(avg_times.values()) / len(avg_times)


def import_module_from_file(file_path: Union[str, Path]):
    """Import a module from a file path.
    Args:
        file_path (Union[str, Path]): Path to the file to import.
    """
    file_path = Path(file_path)
    module_name = file_path.stem
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None:  # import pyx from .so
        # TODO: figure out how to handle pyximport better
        so_files = list(file_path.parent.glob(f"{module_name}.*.so"))
        # pick first one for now
        file_path = so_files[0]
        spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@retry(
    3,
    (
        CythonCompilerError,
        AllTestFailedError,
        IndentationError,
        AllGenerationsFailedError,
    ), # type: ignore
)
def cythonize_function(
    function_path: str, test_function_paths: List[str] = [], refine_depth=2
):
    """Top-level function for optimizing a function.
    Creates new files in the user's workspace with the optimized function and tests.

    Args:
        function_path (str): Path to file with function, e.g. /path/to/file.py::function_name
        test_function_paths (List[str]): Paths to files with test functions, e.g. /path/to/test.py::test_function_name
    """
    evaluated_results = []
    # get the relevant code from the file as a string
    function_file_path = Path(function_path.split("::")[0])
    function_name = function_path.split("::")[1]

    imports = get_imports(function_file_path)
    source = get_source_code_of_function(function_file_path, function_name)
    
    logger.info(f"Optimizing function {function_name} in {function_file_path}")
    render(function_name, evaluated_results, "Generating tests...")

    nr_of_tests = 5
    test_create_results, test_path = generate_tests(function_path, nr_of_tests)
    
    render(function_name, evaluated_results, "Tests generated! Generating code...")

    # get the relevant code from the test files as a string
    coa = CythonCodeOptimizerAssistant()
    results = coa.optimize_code_initial(
        source,
        choices=4,
        import_statements=imports,
        test_code=[test for result in test_create_results for test in result.new_tests],
    )

    render(function_name, evaluated_results, "Optimization started! Ensuring tests are correct ...")

    # TODO: probably not the best way to handle importing the local project
    # see if importlib can help out
    sys.path.append(str(function_file_path.parent))

    # run original one first
    while True:
        try:
            original_timing = run_test_file_with_replacement_function(
                test_path, function_file_path, function_name
            )
            break
        except FaultyTestError as e:
            # We assume this is an error in the generated test,
            # so we delete this test from the file and try again
            logger.exception("Error running original test, deleting faulty test")
            for result in test_create_results:
                if e.test_name in result.new_tests:
                    result.new_tests.remove(e.test_name)
            
            test_path = write_test_results_to_file(test_create_results, function_file_path, function_name, test_path)
            nr_of_tests -= 1

    evaluated_results += [
        EvaluatedOptimizedFunctionResult(
            function_name=function_name,
            test_path=test_path,
            optimized_function_path=function_file_path,
            runtime_ms=original_timing,
            user_feedback="Original function",
            previous_messages=[],
            error="",
            test_that_failed_src="",
        )
    ]
    render(function_name, evaluated_results, "Tests correct! Original function timed. Starting optimization...")

    if nr_of_tests == 0:
        raise AllTestFailedError("All tests failed, could not run original function")

    # evaluate the results
    evaluated_results += evaluate_optimized_function_results(
        function_path, test_path, results
    )
    render(function_name, evaluated_results, "Refining solutions...")
    logger.info("Evaluated results")
    display_ordered_runtimes(evaluated_results, original_timing)

    # refine the best result
    for i in range(refine_depth):
        evaluated_results = sorted(evaluated_results, key=lambda x: x.runtime_ms)
        try:
            best_result = evaluated_results[0]
        except IndexError:
            raise AllGenerationsFailedError("All generations failed")

        refined_results = refine_optimized_function(
            best_result.previous_messages,
            best_result.error,
            best_result.test_that_failed_src,
            best_result.runtime_ms,
            best_result.user_feedback,
            coa,
        )

        # evaluate the refined results
        refined_evaluated_results = evaluate_optimized_function_results(
            str(best_result.optimized_function_path) + "::" + function_name, test_path, refined_results
        )

        logger.info(f"Finished refining function (depth {i})")

        display_ordered_runtimes(
            refined_evaluated_results, original_timing, best_result.runtime_ms
        )
        
        evaluated_results += refined_evaluated_results
        render(function_name, evaluated_results, f"Done refining on generation {i+1}")

    logger.info("Finished optimizing function")
    display_ordered_runtimes(evaluated_results, original_timing)
    render(function_name, evaluated_results, "Tests generated! Starting optimization...")


def evaluate_optimized_function_results(
    function_path: str,
    test_path: str,
    optimization_results: List[
        Tuple[AssistantCodeOptimizationResult, List[ChatCompletionMessage]]
    ],
) -> List[EvaluatedOptimizedFunctionResult]:
    """Evaluate the results of optimizing a function.
    Args:
        function_path (str): Path to the function.
        test_path (str): Path to the test file.
        optimized_function_path (str): Path to the optimized function.
        function_name (str): Name of the function.
    """
    evaluated_results = []
    for idx, (result, previous_messages) in enumerate(optimization_results):
        # Write to file next to original file as *_optimized.pyx
        function_file_path = Path(function_path.split("::")[0])
        function_name = function_path.split("::")[1]
        directory = function_file_path.parent / ".tmp"
        directory.mkdir(parents=True, exist_ok=True)
        opt_pyx_path = directory / f"{function_file_path.stem}_{idx}.pyx"
        with open(opt_pyx_path, "w") as f:
            print(result.import_statements)
            f.write("\n".join(result.import_statements))
            f.write("\n")
            f.write(result.cython_function)

        # compile the optimized function
        try:
            compile_pyx_to_so(opt_pyx_path)
        except CythonCompilerError as e:
            logger.exception(f"Error compiling optimized function {idx}")
            continue

        # then run optimized in seperate process
        # Note: we have to run this in a separate process because the cythonized function
        # can segfault and crash the main process
        # In addition, we can of course parallelize this!
        p = Process(
            target=run_test_file_with_replacement_function,
            args=(test_path, opt_pyx_path, function_name),
        )
        p.start()
        p.join(5)
        exc, tb = p.exception or (None, None)
        if p.exitcode != 0 or exc:
            logger.exception(f"Error running optimized function {idx}")
            continue
        timing = p.result

        # TODO refine errors in the future, for now just log and skip
        # functions that have errors
        error = ""
        test_that_failed_src = ""

        evaluated_results.append(
            EvaluatedOptimizedFunctionResult(
                function_name=function_name,
                test_path=test_path,
                optimized_function_path=opt_pyx_path,
                runtime_ms=timing,
                user_feedback="Try to optimize this function further",
                previous_messages=previous_messages,
                error=error,
                test_that_failed_src=test_that_failed_src,
            )
        )

        render(function_name, evaluated_results, "Creating set of optimized functions...")

    return evaluated_results


def refine_optimized_function(
    previous_messages: List[ChatCompletionMessage],
    error: str,
    test_that_failed_src: str,
    runtime_ms: float,
    user_feedback: str,
    coa: CythonCodeOptimizerAssistant,
) -> List[Tuple[AssistantCodeOptimizationResult, List[ChatCompletionMessage]]]:
    """Refine the optimized function.
    Args:
        previous_messages: List of previous messages.
        error: Error message.
        test_that_failed_src: Source code of the test that failed.
        runtime_ms: Runtime in milliseconds.
        user_feedback: User feedback.
        coa: CythonCodeOptimizerAssistant instance.
    """
    results = coa.refine_code(
        error,
        test_that_failed_src,
        runtime_ms,
        user_feedback,
        choices=4,
        previous_messages=previous_messages,
    )
    return results


def generate_tests(
    function_path: str, number_of_tests: int, existing_test_file_path=None
):
    """Generate tests for a function.
    Args:
        function_path (str): Path to the function to generate tests for.
        number_of_tests (int): Number of tests to generate.
    """
    function_file_path = Path(function_path.split("::")[0])
    function_name = function_path.split("::")[1]

    imports = get_imports(function_file_path)
    source = get_source_code_of_function(function_file_path, function_name)
    tca = PythonTestCreatorAssistant()
    results = tca.create_tests(imports, source, number_of_tests, [])
    
    test_path = write_test_results_to_file(results, function_file_path, function_name, existing_test_file_path)

    return results, test_path

def write_test_results_to_file(results, function_file_path, function_name, existing_test_file_path=None):
    """Write test results to a file.
    Args:
        results (List[EvaluatedOptimizedFunctionResult]): List of results.
        file_path (str): Path to the file to write to.
    """
    if existing_test_file_path:
        with open(existing_test_file_path, "a") as f:
            for result in results:
                for test in result.new_tests:
                    f.write(test)
                    f.write("\n")
        test_path = existing_test_file_path

    else:  # write to new file next to original file
        test_path = function_file_path.parent / f"test_{function_file_path.stem}.py"
        for result in results:
            with open(test_path, "w") as f:
                f.write("# Autogenerated test file\n")
                f.write(f"from {function_file_path.stem} import {function_name}\n")

                for imp in result.import_statements:
                    f.write(imp)
                    f.write("\n")
                for test in result.new_tests:
                    f.write(test)
                    f.write("\n\n")
    return test_path

def compile_pyx_to_so(pyx_path):
    """Compile a pyx file to a shared object file.
    Args:
        pyx_path (str): Path to the pyx file.
    """
    with subprocess.Popen(
        ["cythonize", "-i", "-a", pyx_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as proc:
        proc.stdout = cast(IO[bytes], proc.stdout)
        proc.stderr = cast(IO[bytes], proc.stderr)
        returncode = proc.wait()
        stdout = proc.stdout.read()
        stderr = proc.stderr.read()
        print(stdout)
        print(stderr, file=sys.stderr)
        if returncode != 0:
            raise CythonCompilerError(f"Error running cythonize for {pyx_path}")
