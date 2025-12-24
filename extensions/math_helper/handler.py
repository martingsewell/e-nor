"""
Math Helper Tool Extension

A calculator tool that E-NOR can use programmatically to solve maths problems.
This demonstrates how extensions can be called by E-NOR itself (not just the user)
when E-NOR needs help completing a task.
"""

import random
import re
import math
from pathlib import Path
from core.server.extension_api import ExtensionAPI

# Create API instance
api = ExtensionAPI("math_helper", Path(__file__).parent)

# Safe math operations - only allow these for security
SAFE_FUNCTIONS = {
    'abs': abs,
    'round': round,
    'min': min,
    'max': max,
    'sum': sum,
    'pow': pow,
    'sqrt': math.sqrt,
    'floor': math.floor,
    'ceil': math.ceil,
}

# Fun responses for different situations
CALCULATION_RESPONSES = [
    "The answer is {result}!",
    "I calculated it! It's {result}!",
    "Let me see... {result}!",
    "That equals {result}!",
    "The result is {result}!"
]

TIMES_TABLE_INTRO = [
    "Here's the {n} times table!",
    "Let me show you the {n} times table!",
    "Time to learn the {n} times table!"
]


def safe_eval(expression: str) -> float:
    """
    Safely evaluate a mathematical expression.
    Only allows basic arithmetic and safe math functions.
    """
    # Clean the expression
    expr = expression.strip()

    # Replace common words with operators
    expr = expr.replace('plus', '+')
    expr = expr.replace('minus', '-')
    expr = expr.replace('times', '*')
    expr = expr.replace('multiplied by', '*')
    expr = expr.replace('divided by', '/')
    expr = expr.replace('x', '*')  # Common multiplication symbol
    expr = expr.replace('squared', '**2')
    expr = expr.replace('cubed', '**3')
    expr = expr.replace('to the power of', '**')

    # Only allow digits, operators, parentheses, decimal points, and spaces
    allowed_chars = set('0123456789+-*/.() ')
    if not all(c in allowed_chars for c in expr):
        # Check if it contains function names
        for func_name in SAFE_FUNCTIONS:
            expr = expr.replace(func_name, '')
        if not all(c in allowed_chars for c in expr.replace(',', '')):
            raise ValueError("Expression contains invalid characters")

    # Evaluate safely
    try:
        # Use a restricted namespace with only safe functions
        result = eval(expr, {"__builtins__": {}}, SAFE_FUNCTIONS)
        return result
    except Exception as e:
        raise ValueError(f"Could not calculate: {str(e)}")


async def handle_action(action: str, params: dict = None) -> dict:
    """Handle math helper actions"""
    params = params or {}

    if action == "calculate":
        expression = params.get("expression", "")

        if not expression:
            await api.speak("What would you like me to calculate?")
            return {"success": True, "message": "Waiting for expression", "needs_input": True}

        try:
            result = safe_eval(expression)

            # Format the result nicely
            if isinstance(result, float):
                if result == int(result):
                    result = int(result)
                else:
                    result = round(result, 4)

            # Speak the result
            response = random.choice(CALCULATION_RESPONSES).format(result=result)
            await api.speak(response)

            # Show the calculation in chat
            await api.show_message(f"**{expression}** = **{result}**")

            # Set a thinking->happy emotion transition
            await api.set_emotion("happy")

            return {
                "success": True,
                "expression": expression,
                "result": result,
                "message": f"{expression} = {result}"
            }

        except ValueError as e:
            await api.speak(f"Hmm, I couldn't figure that out. {str(e)}")
            await api.set_emotion("thinking")
            return {"success": False, "error": str(e)}
        except Exception as e:
            await api.speak("Oops! That calculation was too tricky for me!")
            return {"success": False, "error": str(e)}

    elif action == "times_table":
        number = params.get("number", params.get("n", 0))

        if not number:
            # Try to extract a number from common phrases
            await api.speak("Which times table would you like? Give me a number from 1 to 12!")
            return {"success": True, "message": "Waiting for number", "needs_input": True}

        try:
            n = int(number)
            if n < 1 or n > 20:
                await api.speak("Let's stick to numbers between 1 and 20!")
                return {"success": False, "error": "Number out of range"}

            # Build the times table
            intro = random.choice(TIMES_TABLE_INTRO).format(n=n)
            await api.speak(intro)

            table_html = f"""
            <div style="padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; color: white; font-family: Arial, sans-serif;">
                <h2 style="text-align: center; margin-bottom: 20px;">{n} Times Table</h2>
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; max-width: 400px; margin: 0 auto;">
            """

            for i in range(1, 13):
                result = n * i
                table_html += f"""
                    <div style="background: rgba(255,255,255,0.2); padding: 10px; border-radius: 8px; text-align: center; font-size: 1.2em;">
                        {n} x {i} = {result}
                    </div>
                """

            table_html += "</div></div>"

            await api.show_panel(table_html)
            await api.set_emotion("happy")

            return {
                "success": True,
                "number": n,
                "message": f"Showing {n} times table"
            }

        except ValueError:
            await api.speak("I need a number for the times table!")
            return {"success": False, "error": "Invalid number"}

    elif action == "random_number":
        min_val = params.get("min", 1)
        max_val = params.get("max", 100)

        # Check for special cases
        request_type = params.get("type", "number")

        if request_type == "dice" or "dice" in str(params.get("expression", "")):
            result = random.randint(1, 6)
            await api.speak(f"I rolled a {result}!")
            await api.show_message(f"**Dice Roll:** {result}")
        elif request_type == "coin" or "coin" in str(params.get("expression", "")):
            result = random.choice(["Heads", "Tails"])
            await api.speak(f"I flipped... {result}!")
            await api.show_message(f"**Coin Flip:** {result}")
        else:
            result = random.randint(int(min_val), int(max_val))
            await api.speak(f"I picked {result}!")
            await api.show_message(f"**Random Number ({min_val}-{max_val}):** {result}")

        await api.set_emotion("excited")

        return {
            "success": True,
            "result": result,
            "message": f"Generated: {result}"
        }

    return {"success": False, "message": f"Unknown action: {action}"}


async def on_load():
    """Called when extension loads"""
    # Nothing to initialize for the calculator
    pass
