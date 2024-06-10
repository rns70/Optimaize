# Opti🌽

Opti🌽 is a VScode extension for automagically optimizing code. Right now it is able to translate
Python code to heavily optimized Cython code using any OpenAI API compatible LLM.. It is still in the early stages of development, so please report any bugs you find.

Right now the state of the code is a quite a mess, since this was an exploratory project for extension development and developing LLM agents. I will be cleaning up the code and adding more features in the future.

The project has the following components:
    - extension.ts is the main entry point for the extension. 
      - It spawns the main Python process, which is responsible for parsing the Python code, interfacing with LLMms and generating the Cython and Python code.
      - It creates a Websocket server that the Python process can use to communicate with the extension.
      - A WebViewPanel is created that displays the UI, it is fully controlled by the Python process.
    - The Python application (pyoptimaize):
        - Installs in the current environment so that it can run the code in the exact same environment as the user.
        - Uses "ast" to find the right functions and the right imports.
        - Has assistants (homebaked, no LangChain yet for pedagogical purposes) for transforming to Cython code, refining cython code and generating tests. 
        - Can compile the generated Cython code and validate the optimized code against the generated tests.
        - Can refine the optimized code a bit like a genetic algorithm (although, no mutation or crossover yet). 
        - Generates tests and uses the original function to validate the generated tests (it is assumed that the original function is correct).
        - A very quick and mostly dirty way of defining and rendering a GUI. By sending raw HTML over a websocket to the WebViewPanel directly.
