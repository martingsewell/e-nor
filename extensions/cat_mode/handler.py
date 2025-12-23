"""
Cat Mode Extension Handler
Provides fun cat behavior with meowing sounds, purring, and cat personality
"""

import random
import asyncio
from pathlib import Path
from core.server.extension_api import ExtensionAPI

# Create API instance
api = ExtensionAPI("cat_mode", Path(__file__).parent)

# Cat responses and behaviors
CAT_GREETINGS = [
    "Meow! I'm a sleek cat now! 🐱",
    "Purrrr... I'm ready to be fabulous! ✨",
    "Meow meow! Time for some cat adventures! 🐾",
    "Purrfect! I'm feeling very feline today! 😸"
]

CAT_SOUNDS = [
    "Meow!",
    "Mrow mrow!",
    "Purrrrr...",
    "Mew mew!",
    "Prrt prrt!",
    "Meooooow!"
]

CAT_ACTIONS = [
    "stretches gracefully",
    "flicks tail elegantly", 
    "does a little cat yawn",
    "sits with perfect posture",
    "twitches whiskers curiously",
    "does a slow cat blink",
    "arches back in a stretch"
]

CAT_RESPONSES = [
    "Purrr... that was nice!",
    "Meow! I approve of this!",
    "Mrow! More attention please!",
    "You're quite tolerable, human.",
    "Purrrr... I suppose that will do.",
    "Meow! I'm such a magnificent cat!"
]

CAT_NAP_RESPONSES = [
    "Yaaawn... time for a little cat nap... 😴",
    "Purrr... I'm getting sleepy... 💤",
    "Meow... finding the perfect sunny spot... ☀️",
    "Mrow... must find a cozy place to curl up... 🛏️"
]

CAT_STRETCH_RESPONSES = [
    "Mrow... big stretch! Front paws first... 🐾",
    "Purrr... now the back legs... so good! ✨",
    "Meow! That felt purrfect! 😸",
    "Mrow... nothing beats a good cat stretch! 🐱"
]

async def handle_action(action: str, params: dict = None) -> dict:
    """Handle cat mode actions"""
    
    if action == "activate_cat_mode":
        # Show cat overlay with ears and whiskers
        await api.show_face_overlay("cat_ears_whiskers")
        
        # Set cat mode active
        await api.set_mode("cat_mode", True)
        
        # Play activation sound and speak greeting
        await api.play_sound("meow_hello.wav")
        greeting = random.choice(CAT_GREETINGS)
        await api.speak(greeting)
        
        # Set a subtle cat emotion
        await api.set_emotion("content")
        
        # Store that we're in cat mode
        api.set_data("active", True)
        
        return {"success": True, "message": "Cat mode activated! Meow!"}
    
    elif action == "deactivate_cat_mode":
        # Hide cat overlay
        await api.hide_face_overlay("cat_ears_whiskers")
        
        # Deactivate cat mode
        await api.set_mode("cat_mode", False)
        
        # Play goodbye sound and speak
        await api.play_sound("meow_goodbye.wav")
        await api.speak("Mrow... I suppose I can be a regular robot again. Purr!")
        
        # Return to happy emotion
        await api.set_emotion("happy")
        
        # Store that we're not in cat mode anymore
        api.set_data("active", False)
        
        return {"success": True, "message": "Cat mode deactivated"}
    
    elif action == "make_cat_sound":
        # Check if we're in cat mode for extra personality
        is_active = api.get_data("active", False)
        
        if is_active:
            # Play random cat sound
            sound_files = ["meow1.wav", "meow2.wav", "meow3.wav", "purr1.wav", "purr2.wav"]
            sound_file = random.choice(sound_files)
            await api.play_sound(sound_file)
            
            # Speak cat sound with action
            cat_sound = random.choice(CAT_SOUNDS)
            cat_action = random.choice(CAT_ACTIONS)
            await api.speak(f"{cat_sound}")
            
            # Show message with action
            await api.show_message(f"🐱 *{cat_action}* {cat_sound}")
            
            # Set content emotion
            await api.set_emotion("content")
            
            # Sometimes add a follow-up response (cats are less chatty than dogs)
            if random.random() < 0.2:  # 20% chance
                await asyncio.sleep(1.5)
                response = random.choice(CAT_RESPONSES)
                await api.speak(response)
        else:
            # Not in cat mode, just make a simple meow
            await api.play_sound("meow1.wav")
            await api.speak("Meow! (Activate cat mode for more feline fun!)")
        
        return {"success": True, "message": "Meow!"}
    
    elif action == "cat_stretch":
        is_active = api.get_data("active", False)
        
        if is_active:
            # Play a purr sound
            await api.play_sound("purr1.wav")
            
            # Do a sequence of stretch responses
            stretch_response = random.choice(CAT_STRETCH_RESPONSES)
            await api.speak(stretch_response)
            
            # Show stretching action
            await api.show_message("🐱 *does a long, luxurious cat stretch* 🎯")
            
            # Set relaxed emotion
            await api.set_emotion("relaxed")
        else:
            await api.speak("Meow! I need to be in cat mode to do proper stretches!")
        
        return {"success": True, "message": "Stretch complete!"}
    
    elif action == "cat_nap":
        is_active = api.get_data("active", False)
        
        if is_active:
            # Play soft purr
            await api.play_sound("purr2.wav")
            
            # Nap sequence
            nap_response = random.choice(CAT_NAP_RESPONSES)
            await api.speak(nap_response)
            
            # Show sleeping action
            await api.show_message("🐱 *curls up in a perfect cat circle* 😴")
            
            # Set sleepy emotion
            await api.set_emotion("sleepy")
            
            # After a pause, "wake up"
            await asyncio.sleep(3)
            await api.speak("Mrow... that was a nice little nap! 😸")
            await api.set_emotion("content")
        else:
            await api.speak("I need to be in cat mode for proper napping technique!")
        
        return {"success": True, "message": "Nap time!"}
    
    return {"success": False, "message": "Unknown action"}

async def on_load():
    """Called when the extension loads"""
    # Reset cat mode state on load
    api.set_data("active", False)

async def on_voice_trigger(trigger: str, full_text: str) -> str:
    """Handle voice triggers with cat personality"""
    is_active = api.get_data("active", False)
    
    if is_active:
        # In cat mode, be more aloof and selective
        responses = [
            f"Mrow... I heard '{trigger}'... I suppose I could help.",
            f"Purr... '{trigger}'? If I must...",
            f"Meow! I might consider helping with '{trigger}'.",
            None  # Sometimes ignore (cats are independent!)
        ]
        return random.choice(responses)
    else:
        return None  # Let normal handler take over