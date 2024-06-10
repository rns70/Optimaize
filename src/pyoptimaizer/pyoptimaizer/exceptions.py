class AllTestFailedError(Exception):
    pass


class AllGenerationsFailedError(Exception):
    pass


class CodeExecutionError(Exception):
    pass


class CythonCompilerError(Exception):
    pass