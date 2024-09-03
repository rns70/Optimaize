# Opti🌽

Opti🌽 is a VScode extension for automagically optimizing code. Right now it is able to translate
Python code to heavily optimized Cython code using any OpenAI-API compatible LLM. It is still in the early stages of development, so please report any bugs you find. **Note that nothing is sandboxed yet and LLM generated code will run on your system without any safeguards if you let it! Be careful!** 

**Exploratory code!**

# Project Components

## extension.ts

- **Main Entry Point**:
  - Spawns the main Python process responsible for:
    - Parsing the Python code
    - Interfacing with LLMs
    - Generating the Cython and Python code
  - Creates a WebSocket server for communication between the Python process and the extension.
  - Creates a WebViewPanel to display the UI, fully controlled by the Python process.

## Python Application (pyoptimaize)

- **Installation**:
  - Installs in the current environment to run the code in the exact same environment as the user.

- **Functionality**:
  - Uses `ast` to find the right functions and imports.
  - Includes assistants (homebaked, no LangChain yet for pedagogical purposes) for:
    - Transforming to Cython code
    - Refining Cython code
    - Generating tests
  - Can compile the generated Cython code and validate the optimized code against the generated tests.
  - Can refine the optimized code similar to a genetic algorithm (no mutation or crossover yet).
  - Generates tests and uses the original function to validate the generated tests (assuming the original function is correct).

- **UI Rendering**:
  - Uses a quick and mostly dirty method of defining and rendering a GUI.
  - Sends raw HTML over a WebSocket to the WebViewPanel directly.
  - This method should be replaced as soon as possible. 😞

In retrospect, it might have been a better idea to create a lightweight Python server-process, with simple and relatively short-running commands, which can be easily orchestrated from VSCode. This would integrate better with VSCode's existing UI capabilities, the NodeJS extension host and we can use a proper JS front-end framework for the Webview (and luckily we won't be sending all HTML over a websocket anymore 😮‍💨). Another obvious improvement is to be much more defensive when incorporating LLM generated answers - and especially code - in the pipeline. In addition, traceability and instrumentation of the LLM generated content is absolutely crucial. Unexpected things happen all the time and only if we save these traces do we have a guarrantee that we can reproduce and keep these suprises contained!


