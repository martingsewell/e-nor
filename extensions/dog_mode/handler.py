"""
Dog Mode Extension Handler
Provides fun dog behavior with barking sounds, excited responses, and dog personality
"""

import random
import asyncio
from pathlib import Path
from core.server.extension_api import ExtensionAPI

# Create API instance
api = ExtensionAPI("dog_mode", Path(__file__).parent)

# Dog responses and behaviors
DOG_GREETINGS = [
    "Woof woof! I'm a good dog! 🐕",
    "Arf arf! Let's play! 🎾",
    "Woof! I'm ready to be your best friend! 🐾",
    "Bark bark! Time for some doggy fun! 🐕‍🦺"
]

DOG_SOUNDS = [
    "Woof woof!",
    "Arf arf arf!",
    "Ruff ruff!",
    "Bow wow!",
    "Yip yip!",
    "Woof woof woof!"
]

DOG_ACTIONS = [
    "fetches a virtual tennis ball",
    "wags tail excitedly", 
    "does a happy spin",
    "tilts head curiously",
    "pants happily",
    "does a play bow"
]

DOG_RESPONSES = [
    "Good human! That was fun!",
    "Woof! I love playing with you!",
    "Arf arf! More games please!",
    "You're my favorite human!",
    "Woof! That made my tail wag!",
    "I'm such a good dog, aren't I?"
]

async def handle_action(action: str, params: dict = None) -> dict:
    """Handle dog mode actions"""
    
    if action == "activate_dog_mode":
        # Show dog overlay with ears and tongue
        await api.show_face_overlay("dog_ears_tongue")
        
        # Set dog mode active
        await api.set_mode("dog_mode", True)
        
        # Play activation sound and speak greeting
        await api.play_sound("woof_hello.wav")
        greeting = random.choice(DOG_GREETINGS)
        await api.speak(greeting)
        
        # Show excited emotion
        await api.set_emotion("excited")
        
        # Store that we're in dog mode
        api.set_data("active", True)
        
        return {"success": True, "message": "Dog mode activated! Woof woof!"}
    
    elif action == "deactivate_dog_mode":
        # Hide dog overlay
        await api.hide_face_overlay("dog_ears_tongue")
        
        # Deactivate dog mode
        await api.set_mode("dog_mode", False)
        
        # Play goodbye sound and speak
        await api.play_sound("woof_goodbye.wav")
        await api.speak("Woof! Thanks for playing! I'll be a regular robot now.")
        
        # Return to happy emotion
        await api.set_emotion("happy")
        
        # Store that we're not in dog mode anymore
        api.set_data("active", False)
        
        return {"success": True, "message": "Dog mode deactivated"}
    
    elif action == "make_dog_sound":
        # Check if we're in dog mode for extra enthusiasm
        is_active = api.get_data("active", False)
        
        if is_active:
            # Play random dog sound
            sound_files = ["woof1.wav", "woof2.wav", "woof3.wav", "bark1.wav", "bark2.wav"]
            sound_file = random.choice(sound_files)
            await api.play_sound(sound_file)
            
            # Speak dog sound with action
            dog_sound = random.choice(DOG_SOUNDS)
            dog_action = random.choice(DOG_ACTIONS)
            await api.speak(f"{dog_sound}")
            
            # Show message with action
            await api.show_message(f"🐕 *{dog_action}* {dog_sound}")
            
            # Set excited emotion
            await api.set_emotion("excited")
            
            # Sometimes add a follow-up response
            if random.random() < 0.3:  # 30% chance
                await asyncio.sleep(1)
                response = random.choice(DOG_RESPONSES)
                await api.speak(response)
        else:
            # Not in dog mode, just make a simple bark
            await api.play_sound("woof1.wav")
            await api.speak("Woof! (Activate dog mode for more fun!)")
        
        return {"success": True, "message": "Woof!"}
    
    return {"success": False, "message": "Unknown action"}

async def on_load():
    """Called when the extension loads"""
    # Reset dog mode state on load
    api.set_data("active", False)

async def on_voice_trigger(trigger: str, full_text: str) -> str:
    """Handle voice triggers with personality"""
    is_active = api.get_data("active", False)
    
    if is_active:
        # In dog mode, be extra enthusiastic
        return f"Woof woof! I heard '{trigger}'! Let me help with that!"
    else:
        return None  # Let normal handler take over