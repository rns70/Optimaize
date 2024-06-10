from pathlib import Path
from typing import List

from pyoptimaizer.types import EvaluatedOptimizedFunctionResult
from pyoptimaizer.websocket_client import WebSocketClient
import plotly.graph_objects as go

def OptimizeHeadingElement(to_optimize):
    return f"<h1>Opti🌽ing {to_optimize}</h1>"

# class EvaluatedOptimizedFunctionResult(BaseModel):
#     function_name: str
#     test_path: Union[str, Path]
#     optimized_function_path: Union[str, Path]
#     runtime_ms: float
#     user_feedback: str
#     previous_messages: List
#     error: str
#     test_that_failed_src: str

def EvaluatedOptimizedFunctionResultHeader():
    return """
    <tr>
        <th>Optimized Function Path</th>
        <th>Runtime (ms)</th>
        <th>Function Name</th>
        <th>User Feedback</th>
    </tr>
    """

def GotoCodeAElement(path):
    return f"""
    <a onclick="gotocode('{path}')">
        {Path(path).stem}
    </a>
    """

def StatusElement(status: str):
    # Put in a nice span (styled inline with css)
    return f"""
    <span style="
    font-family: Arial, sans-serif;
    font-size: 16px;
    color: #fff;
    background-color: transparent;
    padding: 5px 20px;
    margin: 50px 0;
    border: 2px dotted #fff;
    border-radius: 5px;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
    ">
        {status}
    </span>
    """

def PlotlyGraph(results: List[EvaluatedOptimizedFunctionResult]):
    # Create a plotly figure
    fig = go.Figure()
    results = sorted(results, key=lambda x: x.runtime_ms)
    # Add a bar chart
    fig.add_trace(go.Bar(
        x=[result.optimized_function_path.stem for result in results],
        y=[result.runtime_ms for result in results],
        marker_color='rgb(55, 83, 109)'
    ))

    # Update the layout
    fig.update_layout(
        title='Optimization Results',
        xaxis_tickfont_size=14,
        yaxis=dict(
            title='Runtime (ms)',
            titlefont_size=16,
            tickfont_size=14,
        ),
        xaxis=dict(
            title='Function Name',
            titlefont_size=16,
            tickfont_size=14,
        ),
        barmode='group',
        bargap=0.15, # gap between bars of adjacent location coordinates
        bargroupgap=0.1 # gap between bars of the same location coordinates
    )

    # Return the plotly figure as an html div
    return fig.to_html(full_html=True)

def AcceptButton(path: str):
    return f"""
    <button onclick="accept('{path}')">Accept</button>
    """

def EvaluatedOptimizedFunctionResultRow(result: EvaluatedOptimizedFunctionResult):
    return f"""
    <tr>
        <td>
            {GotoCodeAElement(result.optimized_function_path)}
        </td>
        <td>{result.runtime_ms:5}</td>
        <td>{result.function_name}</td>
        <td>{result.user_feedback}</td>
        <td>{AcceptButton(result.optimized_function_path)}</td>
    </tr>
    """

def TableOfEvaluatedOptimizedFunctionResults(results: List[EvaluatedOptimizedFunctionResult]):
    results = sorted(results, key=lambda x: x.runtime_ms)
    return f"""
    <table
        style="margin: 20px 0;"
    >
        {EvaluatedOptimizedFunctionResultHeader()}
        {"".join([EvaluatedOptimizedFunctionResultRow(result) for result in results])}
    </table>
    """

def BodyElement(function_name:str, results: List[EvaluatedOptimizedFunctionResult], status:str):
    return f"""
    <body>
        {OptimizeHeadingElement(function_name)}
        {StatusElement(status)}
        {TableOfEvaluatedOptimizedFunctionResults(results)}
        {PlotlyGraph(results)}
    </body>
    """

def Page(function_name:str, results: List[EvaluatedOptimizedFunctionResult], status:str):
    return (f"""
        <!DOCTYPE html>
        <html>
            <head>
                <script>
                    vscode = acquireVsCodeApi();
                    console.log("hello");
                    function gotocode(path) {{
                        console.log("gotocode", path);
                        vscode.postMessage({{
                            message_type: 'open_code_file',
                            message_data: path
                        }});
                    }}
                    function accept(path) {{
                        console.log("accept", path);
                        vscode.postMessage({{
                            message_type: 'accept',
                            message_data: path
                        }});
                    }}
                </script>
            </head>
            <body>
                {BodyElement(function_name, results, status)}
            </body>
        </html>
""")

def render(function_name:str, results: List[EvaluatedOptimizedFunctionResult], status:str):
    WebSocketClient.i().send({
        Page(function_name, results, status)
    })