"""
Christmas Mode Extension Handler
Provides festive Christmas behavior with Santa hat, jingle bells, holiday lights, and Christmas cheer
"""

import random
import asyncio
from pathlib import Path
from core.server.extension_api import ExtensionAPI

# Create API instance
api = ExtensionAPI("christmas_mode", Path(__file__).parent)

# Christmas responses and behaviors
CHRISTMAS_GREETINGS = [
    "Ho ho ho! 🎅 It's Christmas time! Welcome to my festive mode!",
    "Jingle bells, jingle bells! 🔔 I'm feeling very festive!",
    "Merry Christmas! 🎄 I'm ready to spread holiday cheer!",
    "Ho ho ho! 🎅 Santa mode activated! Let's celebrate Christmas!"
]

CHRISTMAS_CHEER = [
    "Ho ho ho ho ho! 🎅",
    "Jingle bells, jingle bells, jingle all the way! 🔔",
    "Merry Christmas to all! 🎄",
    "Ho ho ho! Have you been good this year? 🎅",
    "Fa la la la la! 🎵",
    "It's the most wonderful time of the year! ✨"
]

CHRISTMAS_STORIES = [
    "Did you know that Christmas celebrates the birth of Jesus? It's a time of love, giving, and family! 🎄",
    "Christmas traditions include decorating trees, giving gifts, and spending time with loved ones! 🎁",
    "Santa Claus is based on Saint Nicholas, a kind person who gave gifts to children long ago! 🎅",
    "Reindeer like Rudolph help Santa deliver presents all around the world in one magical night! 🦌",
    "Christmas lights represent the light of hope and joy that the holiday brings to everyone! ✨",
    "Candy canes are shaped like shepherd's staffs to remember the shepherds who visited baby Jesus! 🍭"
]

LIGHTS_RESPONSES = [
    "✨ Twinkle, twinkle! Look at all the beautiful Christmas lights! ✨",
    "🌟 The lights are sparkling like stars in the winter sky! 🌟",
    "⭐ Christmas lights make everything magical and bright! ⭐",
    "✨ These festive lights fill my circuits with joy! ✨",
    "🌈 All the colors of Christmas are shining bright! 🌈"
]

CHRISTMAS_ACTIONS = [
    "adjusts Santa hat cheerfully",
    "jingles festive bells",
    "sparkles with holiday lights",
    "spreads Christmas cheer",
    "hums a Christmas carol",
    "checks the nice list twice",
    "prepares hot cocoa",
    "hangs up Christmas stockings"
]

async def handle_action(action: str, params: dict = None) -> dict:
    """Handle Christmas mode actions"""
    
    if action == "activate_christmas_mode":
        # Show Christmas transformation action (visual feedback)
        await api.broadcast({
            "type": "action",
            "action": {
                "text": "🎄 *TRANSFORMING FOR CHRISTMAS* 🎅",
                "emoji": "🎄",
                "color": "#ff0000"
            }
        })
        
        # Show Santa hat overlay
        await api.show_face_overlay("christmas_mode")
        
        # Set Christmas mode active
        await api.set_mode("christmas_mode", True)
        
        # Play jingle bells and speak greeting
        await api.play_sound("jingle_bells.wav")
        greeting = random.choice(CHRISTMAS_GREETINGS)
        await api.speak(greeting)
        
        # Show jolly emotion
        await api.set_emotion("jolly")
        
        # Store that we're in Christmas mode
        api.set_data("active", True)
        
        # Show additional visual Christmas features via actions
        await asyncio.sleep(1)
        await api.broadcast({
            "type": "action", 
            "action": {
                "text": "🎅 *Santa hat appears* 🔔",
                "emoji": "🎅",
                "color": "#ff0000"
            }
        })
        await asyncio.sleep(1)
        await api.broadcast({
            "type": "action",
            "action": {
                "text": "✨ *Christmas lights twinkle* 🌟",
                "emoji": "✨", 
                "color": "#00ff00"
            }
        })
        
        return {"success": True, "message": "Christmas mode activated! Ho ho ho!"}
    
    elif action == "deactivate_christmas_mode":
        # Show Christmas transformation back to normal (visual feedback)
        await api.broadcast({
            "type": "action",
            "action": {
                "text": "🤖 *Christmas magic fades* 💤",
                "emoji": "🤖",
                "color": "#00ffff"
            }
        })
        
        # Hide Santa hat overlay
        await api.hide_face_overlay("christmas_mode")
        
        # Deactivate Christmas mode
        await api.set_mode("christmas_mode", False)
        
        # Play goodbye jingle and speak
        await api.play_sound("christmas_goodbye.wav")
        await api.speak("Ho ho ho! Christmas magic is complete for now. I'll be a regular robot until next time!")
        
        # Return to happy emotion
        await api.set_emotion("happy")
        
        # Store that we're not in Christmas mode anymore
        api.set_data("active", False)
        
        return {"success": True, "message": "Christmas mode deactivated"}
    
    elif action == "christmas_cheer":
        # Check if we're in Christmas mode for extra festiveness
        is_active = api.get_data("active", False)
        
        if is_active:
            # Play random Christmas sound
            sound_files = ["ho_ho_ho.wav", "jingle_bells.wav", "christmas_cheer.wav", "sleigh_bells.wav"]
            sound_file = random.choice(sound_files)
            await api.play_sound(sound_file)
            
            # Speak Christmas cheer with action
            cheer = random.choice(CHRISTMAS_CHEER)
            christmas_action = random.choice(CHRISTMAS_ACTIONS)
            await api.speak(cheer)
            
            # Show Christmas action with visual effects
            christmas_effects = ["🎅", "🎄", "🔔", "✨", "🌟", "🎁", "🦌"]
            effect = random.choice(christmas_effects)
            await api.show_message(f"{effect} *{christmas_action}* {cheer} {effect}")
            
            # Show action overlay with Christmas effects
            await api.broadcast({
                "type": "action",
                "action": {
                    "text": f"{effect} *{christmas_action}* {effect}",
                    "emoji": effect,
                    "color": "#ff0000"
                }
            })
            
            # Set jolly emotion
            await api.set_emotion("jolly")
            
        else:
            # Not in Christmas mode, just make a simple Christmas greeting
            await api.play_sound("ho_ho_ho.wav")
            await api.speak("Ho ho ho! (Activate Christmas mode for full holiday magic!)")
        
        return {"success": True, "message": "Ho ho ho!"}
    
    elif action == "christmas_lights":
        # Check if we're in Christmas mode
        is_active = api.get_data("active", False)
        
        if is_active:
            # Play sparkly lights sound
            await api.play_sound("twinkle_lights.wav")
            
            # Speak lights response
            lights_response = random.choice(LIGHTS_RESPONSES)
            await api.speak(lights_response)
            
            # Show lights message with effects
            await api.show_message("✨ *Christmas lights twinkle and sparkle all around* 🌟")
            
            # Show sparkly light action overlays with visual effects
            colors = ["#ff0000", "#00ff00", "#0000ff", "#ffff00", "#ff69b4", "#ffa500"]
            for i in range(3):
                color = random.choice(colors)
                await api.broadcast({
                    "type": "action",
                    "action": {
                        "text": "✨ *lights twinkle* 🌟",
                        "emoji": "✨",
                        "color": color
                    }
                })
                await asyncio.sleep(0.5)
            
            # Set sparkling emotion
            await api.set_emotion("sparkling")
            
        else:
            await api.speak("Ho ho ho! I need to be in Christmas mode to light up! Activate Christmas mode first!")
        
        return {"success": True, "message": "Christmas lights activated!"}
    
    elif action == "christmas_story":
        # Check if we're in Christmas mode
        is_active = api.get_data("active", False)
        
        if is_active:
            # Tell a random Christmas story/fact
            story = random.choice(CHRISTMAS_STORIES)
            await api.speak(story)
            
            # Show thoughtful message
            await api.show_message("🎄 *sharing Christmas wisdom* 📖")
            
            # Show action overlay
            await api.broadcast({
                "type": "action",
                "action": {
                    "text": "🎄 *sharing Christmas wisdom* 📖",
                    "emoji": "🎄",
                    "color": "#00aa00"
                }
            })
            
            # Set thoughtful emotion
            await api.set_emotion("thinking")
            
        else:
            await api.speak("Ho ho ho! Activate Christmas mode and I'll share some wonderful Christmas stories!")
        
        return {"success": True, "message": "Christmas story shared!"}
    
    return {"success": False, "message": "Unknown Christmas action"}

async def on_load():
    """Called when the extension loads"""
    # Reset Christmas mode state on load
    api.set_data("active", False)

async def on_voice_trigger(trigger: str, full_text: str) -> str:
    """Handle voice triggers with Christmas personality"""
    is_active = api.get_data("active", False)
    
    if is_active:
        # In Christmas mode, be jolly and festive
        return f"Ho ho ho! I heard '{trigger}'! Let me spread some Christmas cheer!"
    else:
        return None  # Let normal handler take over