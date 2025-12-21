"""
Snake Game Extension Handler
Provides a fun Snake game that can be played through voice commands
"""

import random
import asyncio
from pathlib import Path
from core.server.extension_api import ExtensionAPI

# Create API instance
api = ExtensionAPI("snake_game", Path(__file__).parent)

# Encouraging messages for different score ranges
SCORE_MESSAGES = {
    "start": [
        "Let's play Snake! Use the arrow keys to move and try to eat the food!",
        "Snake time! Grow your snake by eating the red food blocks!",
        "Ready to slither? Control your snake with the arrow keys!"
    ],
    "low": [  # 1-5 points
        "Great start! Keep going!",
        "You're getting the hang of it!",
        "Nice moves! Keep growing your snake!"
    ],
    "medium": [  # 6-15 points
        "Awesome! You're doing really well!",
        "Fantastic! Your snake is getting longer!",
        "Great job! You're becoming a Snake master!"
    ],
    "high": [  # 16+ points
        "Incredible! You're amazing at this!",
        "Wow! You're a Snake champion!",
        "Outstanding! That's some serious Snake skills!"
    ],
    "game_over": [
        "Good game! Want to try again?",
        "Nice try! You did great - ready for another round?",
        "Oops! That happens to everyone. Play again?",
        "Good effort! Snake takes practice - try once more!"
    ]
}

async def handle_action(action: str, params: dict = None) -> dict:
    """Handle snake game actions"""
    
    if action == "start_snake_game":
        # Load the game UI
        ui_file = Path(__file__).parent / "ui.html"
        if ui_file.exists():
            with open(ui_file, 'r') as f:
                ui_content = f.read()
            
            # Show the game panel
            await api.show_panel(ui_content)
            
            # Speak encouraging start message
            start_message = random.choice(SCORE_MESSAGES["start"])
            await api.speak(start_message)
            
            # Set excited emotion
            await api.set_emotion("excited")
            
            # Store that the game is active
            api.set_data("game_active", True)
            api.set_data("current_score", 0)
            
            return {"success": True, "message": "Snake game started!"}
        else:
            await api.speak("Oh no! I can't find the Snake game files. Let me check what happened.")
            return {"success": False, "message": "Game UI file not found"}
    
    elif action == "stop_snake_game":
        # Hide the game panel
        await api.hide_panel()
        
        # Get final score if available
        current_score = api.get_data("current_score", 0)
        if current_score > 0:
            await api.speak(f"Final score: {current_score}! Thanks for playing Snake!")
        else:
            await api.speak("Thanks for playing Snake! Come back anytime!")
        
        # Return to happy emotion
        await api.set_emotion("happy")
        
        # Store that game is no longer active
        api.set_data("game_active", False)
        api.set_data("current_score", 0)
        
        return {"success": True, "message": "Snake game stopped"}
    
    elif action == "game_over":
        # Handle game over from the UI
        final_score = params.get("score", 0) if params else 0
        
        # Store the score
        api.set_data("current_score", final_score)
        
        # Give encouraging feedback based on score
        if final_score >= 16:
            message = random.choice(SCORE_MESSAGES["high"])
        elif final_score >= 6:
            message = random.choice(SCORE_MESSAGES["medium"])
        elif final_score >= 1:
            message = random.choice(SCORE_MESSAGES["low"])
        else:
            message = random.choice(SCORE_MESSAGES["game_over"])
        
        await api.speak(f"Game over! You scored {final_score} points. {message}")
        
        return {"success": True, "message": f"Game over - Score: {final_score}"}
    
    elif action == "score_update":
        # Handle score updates from the UI
        new_score = params.get("score", 0) if params else 0
        api.set_data("current_score", new_score)
        
        # Give occasional encouragement
        if new_score > 0 and new_score % 5 == 0:  # Every 5 points
            if new_score >= 16:
                message = random.choice(SCORE_MESSAGES["high"])
            elif new_score >= 6:
                message = random.choice(SCORE_MESSAGES["medium"])
            else:
                message = random.choice(SCORE_MESSAGES["low"])
            
            await api.speak(message)
            await api.set_emotion("excited")
        
        return {"success": True, "message": f"Score updated: {new_score}"}
    
    return {"success": False, "message": "Unknown action"}

async def on_load():
    """Called when the extension loads"""
    # Reset game state on load
    api.set_data("game_active", False)
    api.set_data("current_score", 0)

async def on_voice_trigger(trigger: str, full_text: str) -> str:
    """Handle voice triggers with game personality"""
    is_active = api.get_data("game_active", False)
    
    if is_active:
        # If game is running, be encouraging
        return f"I heard you say '{trigger}'! Focus on the game - you're doing great!"
    else:
        return None  # Let normal handler take over