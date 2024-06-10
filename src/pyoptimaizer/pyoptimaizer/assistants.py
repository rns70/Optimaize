from loguru import logger
from pydantic import BaseModel
from typing import List, Optional, Tuple
import openai
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from pyoptimaizer.prompt import read_instruction_template


class AssistantCodeOptimizationQuery(BaseModel):
    python_code: str
    python_tests: List[str]
    import_statements: List[str] = []
    number_of_optimizations: int = 1


class AssistantCodeOptimizationResult(BaseModel):
    reasoning: str
    cython_function: str
    import_statements: List[str]

class AssistantCodeOptimizationResults(BaseModel):
    optimized_functions: List[AssistantCodeOptimizationResult]

class AssistantCodeOptimizationRefineQuery(BaseModel):
    error: str
    test_that_failed_src: str
    runtime_ms: float
    user_feedback: str


class AssistantCodeTestCreateQuery(BaseModel):
    import_statements: List[str]
    python_function: str
    number_of_tests_to_generate: int
    existing_tests: List[str]


class AssistantCodeTestCreateResult(BaseModel):
    import_statements: List[str]
    new_tests: List[str]


class OpenAIAssistant:
    def __init__(
        self,
        model_preamble: List[dict] = [],
        openai_url: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        openai_org_id: Optional[str] = None,
        default_model: str = "gpt-4o",
        **kwargs
    ):
        """If any of the parameters are none, they will be taken from environment variables.

        For now a RemoteLLM instance must be compatible with the openai api.

        Args:
            openai_url (str, optional): Openai url. Defaults to None.
            openai_api_key (str, optional): Openai api key. Defaults to None.
            openai_org_id (str, optional): Openai org id. Defaults to None.
            kwargs: Additional arguments to pass to openai.OpenAI
        """

        self.default_model = default_model

        self.model_preamble = model_preamble

        self._openai_api = openai.OpenAI(
            base_url=openai_url,
            api_key=openai_api_key,
            organization=openai_org_id,
            **kwargs
        )


class CythonCodeOptimizerAssistant(OpenAIAssistant):
    def __init__(self, **kwargs):
        model_preamble = read_instruction_template("cython_code_optimizer", "v1")
        super().__init__(model_preamble=model_preamble, **kwargs)

    def optimize_code_initial(
        self,
        code: str,
        test_code: List[str] = [],
        choices: int = 1,
        import_statements: List[str] = [],
    ) -> List[Tuple[AssistantCodeOptimizationResult, List[ChatCompletionMessage]]]:
        """Optimize the code using the assistant."""

        llm_query = AssistantCodeOptimizationQuery(
            python_code=code,
            python_tests=test_code,
            import_statements=import_statements,
            number_of_optimizations=2
        )

        llm_query_json = llm_query.model_dump_json()
        code_message = {"role": "user", "content": llm_query_json}

        messages = self.model_preamble + [code_message]
        
        completion = self._openai_api.chat.completions.create(
            messages=messages,
            model=self.default_model,
            response_format={"type": "json_object"},
            n=choices,
        )  # type: ignore

        results = []
        for choice in completion.choices:
            # parse with pydantic
            assert choice.message.content is not None
            try:
                nestedresult = AssistantCodeOptimizationResults.model_validate_json(
                    choice.message.content
                )
                for result in nestedresult.optimized_functions:
                    results.append((result, messages + [choice.message]))
            except Exception as e:
                logger.error("Error parsing result from CodeOptimizationLLM")
                logger.exception(e)

        return results
    
    def refine_code(
        self,
        error: str,
        test_that_failed_src: str,
        runtime_ms: float,
        user_feedback: str,
        choices: int = 4,
        previous_messages: List[ChatCompletionMessage] = [],
        ) -> List[Tuple[AssistantCodeOptimizationResult, List[ChatCompletionMessage]]]:
        """Refine the code using the assistant."""

        llm_query = AssistantCodeOptimizationRefineQuery(
            error=error,
            test_that_failed_src=test_that_failed_src,
            runtime_ms=runtime_ms,
            user_feedback=user_feedback,
        )

        llm_query_json = llm_query.model_dump_json()
        code_message = {"role": "user", "content": llm_query_json}

        messages = self.model_preamble + previous_messages + [code_message]
        
        completion = self._openai_api.chat.completions.create(
            messages=messages,
            model=self.default_model,
            response_format={"type": "json_object"},
            n=choices,
        )

        results = []
        for choice in completion.choices:
            # parse with pydantic
            assert choice.message.content is not None
            try:
                nestedresult = AssistantCodeOptimizationResults.model_validate_json(
                    choice.message.content
                )
                for result in nestedresult.optimized_functions:
                    results.append((result, messages + [choice.message]))
            except Exception as e:
                logger.error("Error parsing result from CodeOptimizationLLM")
                logger.exception(e)

        return results




class PythonTestCreatorAssistant(OpenAIAssistant):
    def __init__(self, **kwargs):
        model_preamble = read_instruction_template("python_test_creator", "v1")
        super().__init__(model_preamble=model_preamble, **kwargs)

    def create_tests(
        self,
        import_statements: List[str],
        python_function: str,
        number_of_tests_to_generate: int,
        existing_tests: List[str],
        choices: int = 1,
    ) -> List[AssistantCodeTestCreateResult]:
        """Create tests for the code using the assistant."""

        llm_query = AssistantCodeTestCreateQuery(
            import_statements=import_statements,
            python_function=python_function,
            number_of_tests_to_generate=number_of_tests_to_generate,
            existing_tests=existing_tests,
        )

        llm_query_json = llm_query.model_dump_json()
        code_message = {"role": "user", "content": llm_query_json}

        messages = self.model_preamble + [code_message]

        completion = self._openai_api.chat.completions.create(
            messages=messages,
            model=self.default_model,
            response_format={"type": "json_object"},
            n=choices,
        )  # type: ignore

        results: List[AssistantCodeTestCreateResult] = []
        for choice in completion.choices:
            # parse with pydantic
            assert choice.message.content is not None
            try:
                result = AssistantCodeTestCreateResult.model_validate_json(
                    choice.message.content
                )
                results.append(result)
            except Exception as e:
                logger.exception("error parsing result from PythonTestCreatorAssistant")
            
            

        return results
