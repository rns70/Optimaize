from typing import List
from loguru import logger
from pyoptimaizer.types import EvaluatedOptimizedFunctionResult

def display_ordered_runtimes(results: List[EvaluatedOptimizedFunctionResult], original_time: float, parent_time: float = None):
    results = sorted(results, key=lambda x: x.runtime_ms)
    to_print = []
    to_print.append(f"Original Runtime: {original_time}ms")
    to_print.append(f"Parent Runtime: {parent_time}ms")
    for result in results:
        to_print.append(f"Function: {result.optimized_function_path} Runtime: {result.runtime_ms}ms")
    logger.info("\n".join(to_print))