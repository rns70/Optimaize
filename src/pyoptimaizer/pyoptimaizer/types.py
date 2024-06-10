from pydantic import BaseModel


from pathlib import Path
from typing import List, Union


class EvaluatedOptimizedFunctionResult(BaseModel):
    function_name: str
    test_path: Union[str, Path]
    optimized_function_path: Union[str, Path]
    runtime_ms: float
    user_feedback: str
    previous_messages: List
    error: str
    test_that_failed_src: str