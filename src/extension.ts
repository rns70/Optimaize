// The module 'vscode' contains the VS Code extensibility API
// Import the module and reference it with the alias vscode in your code below
import * as vscode from "vscode";
import { commands, InputBoxOptions } from "vscode";
import { PythonExtension } from "@vscode/python-extension";
import WebSocket from "ws";

async function get_all_function_names(uri: vscode.Uri): Promise<string[]> {
  const symbols: vscode.DocumentSymbol[] = await commands.executeCommand(
    "vscode.executeDocumentSymbolProvider",
    uri
  );
  const function_names = symbols
    .filter((symbol) => symbol.kind == vscode.SymbolKind.Function)
    .map((symbol) => symbol.name);
  return function_names;
}

/**
 * Prepares the Python environment for the Optimaize extension.
 *
 * Note: it is a bit nasty to dirty the users environment with our new package.
 * but it is far easier than the alternative of packaging the user's python
 * code and running it in a separate environment.
 *
 * @param context - The extension context.
 * @returns A promise that resolves when the Python environment is prepared.
 */
async function preparePythonEnvironment(
  context: vscode.ExtensionContext,
  terminal: vscode.Terminal
): Promise<void> {
  const pythonApi = await PythonExtension.api();
  const environmentPath = pythonApi.environments.getActiveEnvironmentPath();
  const environment = await pythonApi.environments.resolveEnvironment(
    environmentPath
  );
  if (!environment) {
    return;
  }
  const pythonExePath = environment.executable.uri?.fsPath;
  if (!pythonExePath) {
    return;
  }

  // Check if we have pip installed the package python-optimaizer,
  // if not install it.
  // Get this extension path
  const extensionPath = context.extensionUri;

  const pythonOptimaizerPath = vscode.Uri.joinPath(
    extensionPath,
    "src/pyoptimaizer"
  );

  // TODO: error handling and spawn the process in a different way or use a terminalwrapper!

  terminal.sendText(
    `"${pythonExePath}" -m pip install -e "${pythonOptimaizerPath.fsPath}"`
  );
}

let websocket: WebSocket.Server | undefined = undefined;

export function activate(context: vscode.ExtensionContext) {
  console.log('Congratulations, your extension "optimaize" is now active!');

  let first_command_done = false;
  let terminal: vscode.Terminal | undefined = undefined;

  let disposable = vscode.commands.registerCommand(
    "optimaize.cythonize_function",
    async () => {
      if (terminal === undefined) {
        terminal = vscode.window.createTerminal({
          name: "Optimaize",
          hideFromUser: false,
          isTransient: true,
		  env: {"OPENAI_API_KEY": process.env["OPENAI_API_KEY"]}
        });
      }
      if (!first_command_done) {
        await preparePythonEnvironment(context, terminal);
        first_command_done = true;
      }
      // The code you place here will be executed every time your command is executed
      // Display a message box to the user
      let pos = vscode.window.activeTextEditor?.selection.active;
      let doc = vscode.window.activeTextEditor?.document;

      if (!pos || !doc) {
        return;
      }

      // Example union typing for a variable
      let documentSymbols:
        | vscode.DocumentSymbol[]
        | vscode.SymbolInformation[] = await commands.executeCommand(
        "vscode.executeDocumentSymbolProvider",
        doc.uri
      );

      let pythonApi = await PythonExtension.api();
      const environmentPath = pythonApi.environments.getActiveEnvironmentPath();
      const environment = await pythonApi.environments.resolveEnvironment(
        environmentPath
      );
      if (!environment) {
        return;
      }

      let pythonExePath = environment.executable.uri?.fsPath;

      for (let symbol of documentSymbols) {
        if (
          Object.hasOwn(symbol, "range") &&
          symbol.kind == vscode.SymbolKind.Function
        ) {
          symbol = symbol as vscode.DocumentSymbol;
          let the_range = symbol.range;
          let the_name = symbol.name;

          if (the_range.contains(pos)) {
            vscode.window.showInformationMessage("Cythonizing " + the_name);
            const the_code = doc.getText(the_range);
            console.log(
              `Optimizing ${the_name} in ${doc.fileName} with code:\n${the_code}`
            );

            const val = await selectTestFunction();
            const testFilePathstr = "";
            const testFunctionNamestr = "";
            if (val) {
              const testFilePath = val[1].fsPath;
              const testFunctionName = val[0];
            }

            //open a webview to show the results
            const panel = vscode.window.createWebviewPanel(
              "Optimaize",
              "Optimaize",
              vscode.ViewColumn.Two,
              {enableScripts: true, retainContextWhenHidden: true},
            );
            // view panel and put on the right side
            panel.reveal(vscode.ViewColumn.Two);
            // receive panel messages
            panel.webview.onDidReceiveMessage(
              ({message_type, message_data}) => {
                console.log(`Received message from webview: ${message_type}`);
                if (message_type === "stop") {
                  terminal?.sendText("exit");
                }
                if (message_type === "open_code_file") {
                  vscode.workspace.openTextDocument(message_data).then(doc => {
                    vscode.window.showTextDocument(doc, vscode.ViewColumn.One);
                  });
                }
                if (message_type === "accept") {
                  const optimized_path = message_data;
                  const original_path = doc.uri.fsPath;
                  const new_path = original_path.replace(".py", "_optimized.pyx");
                  // log all
                  console.log(`Optimized path: ${optimized_path}, original path: ${original_path}, new path: ${new_path}`);
                  // move the optimized file to the original file path
                  vscode.workspace.fs.copy(vscode.Uri.file(optimized_path), vscode.Uri.file(new_path), {overwrite: true});
                  return;
                }

              },
              undefined,
              context.subscriptions
            );

            // create a websocket server to listen for the results
            // and send them to the webview
            console.log("Starting websocket server");
            if (websocket) {
              websocket.close();
              websocket = undefined;
            }

            if (!websocket) {
              websocket = new WebSocket.Server({ port: 8085 });
              websocket.on("connection", (ws) => {
                ws.on("message", (message) => {
                  console.log(`Received message => ${message}`);
                  panel.reveal(vscode.ViewColumn.Two);
                  panel.webview.html = message.toString();
                });

                ws.on("close", () => {
                  console.log("Client disconnected");
                });
              });
            }
            
            // execute python
            terminal.sendText(
              `"${pythonExePath}" -m pyoptimaizer "${doc.fileName}::${the_name}" "${testFilePathstr}" "${testFunctionNamestr}"`
            );

          }
        }
      }
    }
  );

  context.subscriptions.push(disposable);
}

async function selectTestFunction(): Promise<[string, vscode.Uri] | undefined> {
  // Ask if the user wants to select a test function
  const yesOption: vscode.MessageItem = { title: "Yes" };
  const noOption: vscode.MessageItem = { title: "No" };
  const messageOptions: vscode.MessageOptions = {
    modal: true,
  };
  const message = "Do you want to select a test function?";
  const response = await vscode.window.showInformationMessage(
    message,
    messageOptions,
    yesOption,
    noOption
  );

  if (response === noOption) {
    return;
  }

  // Select a path first
  const openDialogOptions: vscode.OpenDialogOptions = {
    canSelectFiles: true,
    canSelectFolders: false,
    title: "Select a file containing a test function",
  };
  const dialogResult = await vscode.window.showOpenDialog(openDialogOptions);
  if (!dialogResult) {
    return;
  }
  const testFilePath = dialogResult[0];

  // Show input box to select a test function
  const testFunctionNames = await get_all_function_names(testFilePath);
  const quickPickOptions: vscode.QuickPickOptions = {
    canPickMany: false,
    title: "Select a test function",
  };
  const testFunctionName = await vscode.window.showQuickPick(
    testFunctionNames,
    quickPickOptions
  );
  if (!testFunctionName) {
    return;
  }
  return [testFunctionName, testFilePath];
}

// This method is called when your extension is deactivated
export function deactivate() {}
