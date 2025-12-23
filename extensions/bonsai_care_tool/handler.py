"""
Bonsai Care Tool Extension Handler
A helpful guide for caring for bonsai trees
"""

import random
import json
from datetime import datetime, timedelta
from pathlib import Path
from core.server.extension_api import ExtensionAPI

# Create API instance
api = ExtensionAPI("bonsai_care_tool", Path(__file__).parent)

# Bonsai care tips and information
CARE_TIPS = [
    "Water when the soil feels slightly dry, but not completely dried out",
    "Place your bonsai near a window with bright, indirect light",
    "Turn your bonsai regularly so all sides get equal light",
    "Use well-draining bonsai soil mix for healthy roots",
    "Feed your bonsai with diluted liquid fertilizer every 2-4 weeks during growing season",
    "Trim dead, damaged, or overgrown branches to keep your tree healthy",
    "Repot every 1-3 years depending on growth and root development"
]

WATERING_ADVICE = [
    "Check soil moisture daily by inserting your finger about 1 inch into the soil",
    "Water thoroughly until water drains from the bottom holes",
    "In summer, you may need to water daily; in winter, every few days",
    "Use room temperature water - avoid very cold or hot water",
    "Water in the morning so your bonsai has all day to absorb moisture",
    "If soil is very dry, water slowly to prevent runoff"
]

TRIMMING_TIPS = [
    "Use clean, sharp bonsai scissors or pruning shears",
    "Remove dead, diseased, or crossing branches first",
    "Trim back to just above a leaf node or bud",
    "Don't remove more than 1/3 of the foliage at once",
    "Best time to trim is during active growing season (spring/summer)",
    "Pinch new growth with fingers for gentle shaping"
]

BONSAI_FACTS = [
    "Bonsai is the Japanese art of growing miniature trees in containers",
    "The word 'bonsai' means 'planted in a container' in Japanese",
    "Some bonsai trees are hundreds of years old!",
    "Any tree species can potentially become a bonsai",
    "Bonsai requires patience - it can take years to achieve the desired shape",
    "The oldest known bonsai tree is over 1000 years old",
    "Bonsai originated in China and was later refined in Japan"
]

SEASONAL_REMINDERS = {
    "spring": "Time for repotting, increased watering, and regular feeding",
    "summer": "Watch for pests, water daily, and continue regular feeding",
    "autumn": "Reduce feeding, prepare for dormancy, collect seeds",
    "winter": "Water less frequently, protect from frost, no fertilizing"
}

async def handle_action(action: str, params: dict = None) -> dict:
    """Handle bonsai care actions"""
    
    try:
        if action == "show_bonsai_guide":
            await show_main_guide()
            return {"success": True, "message": "Bonsai care guide displayed"}
            
        elif action == "watering_advice":
            tip = random.choice(WATERING_ADVICE)
            await api.speak(f"Here's a watering tip: {tip}")
            await api.show_message(f"💧 **Watering Tip**: {tip}")
            return {"success": True, "message": "Watering advice provided"}
            
        elif action == "trimming_advice":
            tip = random.choice(TRIMMING_TIPS)
            await api.speak(f"For trimming: {tip}")
            await api.show_message(f"✂️ **Trimming Tip**: {tip}")
            return {"success": True, "message": "Trimming advice provided"}
            
        elif action == "set_reminder":
            await set_care_reminder()
            return {"success": True, "message": "Reminder set"}
            
        elif action == "bonsai_facts":
            fact = random.choice(BONSAI_FACTS)
            await api.speak(f"Here's a cool bonsai fact: {fact}")
            await api.show_message(f"🌱 **Bonsai Fact**: {fact}")
            return {"success": True, "message": "Bonsai fact shared"}
            
        else:
            return {"success": False, "message": f"Unknown action: {action}"}
            
    except Exception as e:
        await api.speak("Sorry, I had trouble with the bonsai care tool!")
        return {"success": False, "error": str(e)}

async def show_main_guide():
    """Display the main bonsai care guide"""
    child_name = api.get_child_name()
    
    # Show comprehensive care panel
    care_html = f"""
    <div class="bonsai-guide" style="padding: 20px; max-width: 600px; font-family: Arial, sans-serif;">
        <h2 style="color: #2d5016; margin-bottom: 20px;">🌲 Bonsai Care Guide for {child_name}</h2>
        
        <div class="care-section" style="margin-bottom: 20px; padding: 15px; background: #f0f8f0; border-radius: 8px;">
            <h3 style="color: #2d5016; margin-top: 0;">💧 Watering</h3>
            <ul style="margin: 10px 0;">
                <li>Check soil daily with your finger</li>
                <li>Water when top inch feels dry</li>
                <li>Water thoroughly until it drains</li>
                <li>Morning watering is best</li>
            </ul>
        </div>
        
        <div class="care-section" style="margin-bottom: 20px; padding: 15px; background: #fff8e1; border-radius: 8px;">
            <h3 style="color: #e65100; margin-top: 0;">☀️ Light & Location</h3>
            <ul style="margin: 10px 0;">
                <li>Bright, indirect sunlight</li>
                <li>Near a window is perfect</li>
                <li>Turn weekly for even growth</li>
                <li>Protect from harsh wind</li>
            </ul>
        </div>
        
        <div class="care-section" style="margin-bottom: 20px; padding: 15px; background: #e8f4fd; border-radius: 8px;">
            <h3 style="color: #1976d2; margin-top: 0;">✂️ Pruning & Trimming</h3>
            <ul style="margin: 10px 0;">
                <li>Use clean, sharp tools</li>
                <li>Remove dead branches first</li>
                <li>Trim back to leaf nodes</li>
                <li>Best in spring/summer</li>
            </ul>
        </div>
        
        <div class="care-section" style="margin-bottom: 20px; padding: 15px; background: #fce4ec; border-radius: 8px;">
            <h3 style="color: #c2185b; margin-top: 0;">🌱 Feeding</h3>
            <ul style="margin: 10px 0;">
                <li>Diluted liquid fertilizer</li>
                <li>Every 2-4 weeks in growing season</li>
                <li>Less in winter</li>
                <li>Follow package instructions</li>
            </ul>
        </div>
        
        <div style="text-align: center; margin-top: 20px; padding: 15px; background: #f5f5f5; border-radius: 8px;">
            <p style="margin: 0; color: #666;">Remember: Bonsai care is a peaceful, rewarding hobby that teaches patience!</p>
        </div>
    </div>
    """
    
    await api.show_panel(care_html)
    await api.speak(f"Here's your complete bonsai care guide, {child_name}! Take your time reading through each section.")

async def set_care_reminder():
    """Set a care reminder for the user"""
    child_name = api.get_child_name()
    
    # Get current reminders
    reminders = api.get_data("reminders", [])
    
    # Add a new reminder for tomorrow
    tomorrow = datetime.now() + timedelta(days=1)
    new_reminder = {
        "date": tomorrow.strftime("%Y-%m-%d"),
        "task": "Check bonsai soil moisture",
        "created": datetime.now().isoformat()
    }
    
    reminders.append(new_reminder)
    api.set_data("reminders", reminders)
    
    # Get current season advice
    month = datetime.now().month
    if month in [3, 4, 5]:
        season = "spring"
    elif month in [6, 7, 8]:
        season = "summer"
    elif month in [9, 10, 11]:
        season = "autumn"
    else:
        season = "winter"
    
    seasonal_tip = SEASONAL_REMINDERS[season]
    
    await api.speak(f"I've set a reminder for tomorrow to check your bonsai soil, {child_name}!")
    await api.show_message(f"📅 **Reminder Set**: Check bonsai soil tomorrow")
    await api.show_message(f"🌸 **{season.title()} Care**: {seasonal_tip}")

async def on_load():
    """Called when extension loads"""
    # Initialize any data if needed
    if not api.get_data("initialized", False):
        api.set_data("reminders", [])
        api.set_data("initialized", True)