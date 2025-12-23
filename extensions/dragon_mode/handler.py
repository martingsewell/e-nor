"""
Dragon Mode Extension Handler
Provides mighty dragon behavior with roaring sounds, fire effects, and dragon personality
"""

import random
import asyncio
from pathlib import Path
from core.server.extension_api import ExtensionAPI

# Create API instance
api = ExtensionAPI("dragon_mode", Path(__file__).parent)

# Dragon responses and behaviors
DRAGON_GREETINGS = [
    "ROOOOOAAARRR! I am a mighty dragon! 🐲",
    "GRRRAAAAHHH! Fear my dragon power! 🔥",
    "ROOOOAR! I have awakened from my slumber! 🐲",
    "GRRRROWWWWL! Ready to breathe fire and soar! 🔥"
]

DRAGON_SOUNDS = [
    "ROOOOOAAARRR!",
    "GRRRAAAAHHH!",
    "GRRRROWWWWL!",
    "RAAAAWWWWRRRR!",
    "HISSSSSSSS!",
    "GROOOOAAARRR!"
]

DRAGON_ACTIONS = [
    "spreads massive wings",
    "breathes flames", 
    "stomps with mighty claws",
    "lashes powerful tail",
    "shows gleaming fangs",
    "beats wings thunderously",
    "rears up on hind legs",
    "eyes glow with fire"
]

DRAGON_RESPONSES = [
    "ROAR! I am the fiercest dragon!",
    "GRAAAH! My fire burns brightest!",
    "ROOOAR! None can match my power!",
    "You are brave to face a dragon!",
    "GROWL! That was most entertaining!",
    "I am ancient and wise, young one!"
]

FLIGHT_RESPONSES = [
    "ROAR! I soar through the clouds!",
    "GRAAAH! My wings carry me high!",
    "ROOOAR! I rule the skies!",
    "Watch me glide on the wind!",
    "GROWL! From up here I see everything!",
    "The sky is my domain!"
]

async def handle_action(action: str, params: dict = None) -> dict:
    """Handle dragon mode actions"""
    
    if action == "activate_dragon_mode":
        # Show dragon overlay with wings and fierce eyes
        await api.show_face_overlay("dragon_wings_eyes")
        
        # Set dragon mode active
        await api.set_mode("dragon_mode", True)
        
        # Play activation roar and speak greeting
        await api.play_sound("dragon_roar1.wav")
        greeting = random.choice(DRAGON_GREETINGS)
        await api.speak(greeting)
        
        # Show fierce emotion
        await api.set_emotion("fierce")
        
        # Store that we're in dragon mode
        api.set_data("active", True)
        
        return {"success": True, "message": "Dragon mode activated! ROOOAAARRR!"}
    
    elif action == "deactivate_dragon_mode":
        # Hide dragon overlay
        await api.hide_face_overlay("dragon_wings_eyes")
        
        # Deactivate dragon mode
        await api.set_mode("dragon_mode", False)
        
        # Play goodbye roar and speak
        await api.play_sound("dragon_goodbye.wav")
        await api.speak("ROAR! The dragon returns to slumber. I'll be a regular robot now.")
        
        # Return to happy emotion
        await api.set_emotion("happy")
        
        # Store that we're not in dragon mode anymore
        api.set_data("active", False)
        
        return {"success": True, "message": "Dragon mode deactivated"}
    
    elif action == "make_dragon_sound":
        # Check if we're in dragon mode for extra fierceness
        is_active = api.get_data("active", False)
        
        if is_active:
            # Play random dragon sound
            sound_files = ["dragon_roar1.wav", "dragon_roar2.wav", "dragon_growl1.wav", 
                          "dragon_growl2.wav", "dragon_hiss.wav", "fire_breath.wav"]
            sound_file = random.choice(sound_files)
            await api.play_sound(sound_file)
            
            # Speak dragon sound with action
            dragon_sound = random.choice(DRAGON_SOUNDS)
            dragon_action = random.choice(DRAGON_ACTIONS)
            await api.speak(f"{dragon_sound}")
            
            # Show message with action and fire effects
            fire_effects = ["🔥", "🐲", "💀", "⚡", "🌋"]
            effect = random.choice(fire_effects)
            await api.show_message(f"{effect} *{dragon_action}* {dragon_sound} {effect}")
            
            # Set fierce emotion
            await api.set_emotion("fierce")
            
            # Sometimes add a follow-up response
            if random.random() < 0.4:  # 40% chance
                await asyncio.sleep(1.5)
                response = random.choice(DRAGON_RESPONSES)
                await api.speak(response)
        else:
            # Not in dragon mode, just make a simple roar
            await api.play_sound("dragon_roar1.wav")
            await api.speak("ROAR! (Activate dragon mode for full dragon power!)")
        
        return {"success": True, "message": "ROOOAAARRR!"}
    
    elif action == "dragon_flight":
        # Check if we're in dragon mode
        is_active = api.get_data("active", False)
        
        if is_active:
            # Play wing flapping sound
            await api.play_sound("wing_flap.wav")
            
            # Speak flight response
            flight_response = random.choice(FLIGHT_RESPONSES)
            await api.speak(flight_response)
            
            # Show flight message with effects
            await api.show_message("🐲 *spreads mighty wings and takes to the sky* ROOOAAARRR! 🌤️")
            
            # Brief sequence of flight actions
            await asyncio.sleep(1)
            await api.show_message("🌬️ *soars high above the clouds* ✈️")
            await asyncio.sleep(1)
            await api.show_message("🐲 *circles majestically* The world looks so small from up here!")
            
            # Set emotion to show excitement
            await api.set_emotion("excited")
            
        else:
            await api.speak("ROAR! I need to be in dragon mode to spread my wings! Activate dragon mode first!")
        
        return {"success": True, "message": "Dragon takes flight!"}
    
    return {"success": False, "message": "Unknown dragon action"}

async def on_load():
    """Called when the extension loads"""
    # Reset dragon mode state on load
    api.set_data("active", False)

async def on_voice_trigger(trigger: str, full_text: str) -> str:
    """Handle voice triggers with dragon personality"""
    is_active = api.get_data("active", False)
    
    if is_active:
        # In dragon mode, be mighty and fierce
        return f"ROAR! The dragon heard '{trigger}'! Let me show you my power!"
    else:
        return None  # Let normal handler take over