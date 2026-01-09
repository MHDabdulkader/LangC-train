from dotenv import load_dotenv
import json
import re
import tempfile
from pathlib import Path
from langchain_core.tools import tool

# DuckDuckGo for web search integration
from ddgs import DDGS

load_dotenv()
##########################################
#
#   Tools in order of usage in agent.py
#
##########################################


# langchain tool or runnable
@tool
def web_search(query: str, num_result: int = 5) -> str:
    """Search the web using DuckDuckGo.

    Args:
        query (str): Search query string
        num_result (int, optional): Number of results to return. Defaults to 5.

    Returns:
        Formatted search results with titles, descriptions and URLs
    """
    try:
        results = list(
            DDGS().text(
                query=query,
                max_results=num_result,
                region="us-en",
                timelimit="d",
                backend="google, brave, bing, duckduckgo",
            )
        )

        if not results:
            return f"No results found for '{query}'"

        formatted_results = [f"Search results for '{query}':\n"]
        for i, result in enumerate(results, 1):
            title = result.get("title", "No title")
            body = result.get("body", "No description available")
            href = result.get("href", "")
            formatted_results.append(f"{i}. **{title}**\n {body}\n {href}")

        return "\n\n".join(formatted_results)

    except Exception as e:
        return f"Search error: {str(e)}"


# Tool  agent model instance


@tool
def calculate(expression: str) -> str:
    """Safety evaluate mathematical expressions using AST parse

    Args:
        expression (str): Mathematical expression string to evaluate

    Returns:
        str: String with Calculation result or error message

    Supports arithmetic, math function (sin, cos, sqrt, log) and constants(pi, e)
    """

    try:
        import ast
        import math

        # Parse the expression into an AST
        node = ast.parse(expression, mode="eval")

        # Define allow node types for safe evaluation
        allowed_nodes = {
            ast.Expression,
            ast.Constant,
            ast.Num,
            ast.BinOp,
            ast.UnaryOp,
            ast.Add,
            ast.Sub,
            ast.Mult,
            ast.Div,
            ast.Mod,
            ast.Pow,
            ast.USub,
            ast.UAdd,
            ast.Name,
            ast.Load,
            ast.Call,
            ast.keyword,
        }

        # Define allowed functions
        allow_functions = {
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "sum": sum,
            "pow": pow,
            "sqrt": lambda x: x**0.5,
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "log": math.log,
            "pi": math.pi,
            "e": math.e,
            "log2": math.log2,
        }
        # Check all nodes allowed!
        for node_item in ast.walk(node):
            if type(node_item) not in allowed_nodes:
                return f"Error: Unsupport operation: {type(node_item).__name__}"

        # Evaluate Safely
        result = eval(
            compile(node, "<string>", "eval"), {"__builtins__": {}}, allow_functions
        )

        return f"{expression} = {result}"

    except SyntaxError:
        return "Error: Invalid mathematical expression"

    except ZeroDivisionError:
        return "Error: Division by zero"

    except Exception as e:
        return f"Error: {str(e)}"


# Tool  agent model instance
@tool
def analyze_data(data: list, operation: str) -> str:
    """
    Dynamic pandas data analysis tool.

    Args:
        data (list): List of dictionaries to convert to DataFrame
        operation (str): Pandas operation string (e.g., 'df.describe()', 'df.groupby("col").sum()')

    Returns:
        str: String respresentation of analysis result or error message
    """

    try:
        import pandas as pd
        import numpy as np

    except ImportError as e:
        return f"Missing dependency: {e}"

    try:
        if not data or not isinstance(data, list):
            return "Data must be a non-empty list"

        # Convert df
        try:
            df = pd.DataFrame(data)
        except Exception as e:
            return f"Failed to create DataFrame: {str(e)}"

        if df.empty:
            return "Empty dataframe created"

        # Default operation
        if not operation or not isinstance(operation, str):
            operation = "df.describe()"

        # Basic Validation - operation should reference 'df'
        if "df" not in operation:
            return "Operation must reference df"

        # Executed operation with restricted namespace
        namespace = {"df": df, "pd": pd, "np": np}
        result = eval(operation, {"__builtins__": {}}, namespace)

        if isinstance(result, (pd.DataFrame, pd.Series)):
            return result.to_string()
        else:
            return str(result)

    except SyntaxError:
        return "Invalid operation syntax"
    except NameError as e:
        return f"Invalid reference: {e}"
    except Exception as e:
        return f"Errors: {str(e)}"
