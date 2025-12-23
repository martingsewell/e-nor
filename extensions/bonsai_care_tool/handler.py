"""
Bonsai Care Tool Extension Handler
Helps with bonsai care tips, watering schedules, and reminders
"""

import random
from datetime import datetime, timedelta
from pathlib import Path
from core.server.extension_api import ExtensionAPI

# Create API instance
api = ExtensionAPI("bonsai_care_tool", Path(__file__).parent)

# Bonsai care tips and advice
GENERAL_TIPS = [
    "Bonsai trees need bright, indirect sunlight for most of the day!",
    "Check the soil daily - it should be slightly damp but not soggy.",
    "Bonsai trees grow slowly, so be patient with your little tree friend!",
    "Turn your bonsai a quarter turn every week so all sides get equal light.",
    "Never let your bonsai completely dry out - they need consistent moisture.",
    "Bonsai love fresh air, so open a window nearby when weather is nice!"
]

WATERING_TIPS = [
    "Water when the top inch of soil feels dry to touch.",
    "Water slowly until it drains from the bottom holes.",
    "Use a watering can with a fine nozzle or spray bottle.",
    "Most bonsai need water every 2-3 days in summer, less in winter.",
    "Morning is the best time to water your bonsai.",
    "If leaves turn yellow, you might be watering too much!"
]

TRIMMING_TIPS = [
    "Use small, sharp scissors made for bonsai trimming.",
    "Trim dead, damaged, or crossing branches first.",
    "Cut just above a leaf or bud to encourage new growth.",
    "Spring is the best time for major trimming.",
    "Pinch soft new growth with your fingers instead of cutting.",
    "Don't trim more than 1/3 of the tree at once - that's too much!"
]

SEASONAL_CARE = {
    "spring": "Spring is growing season! Water more often and start fertilizing monthly.",
    "summer": "Summer heat means more watering - check daily and keep in shade during hottest hours.",
    "fall": "Fall is time to reduce watering and stop fertilizing as growth slows down.",
    "winter": "Winter bonsai need less water and should be protected from freezing temperatures."
}

async def handle_action(action: str, params: dict = None) -> dict:
    """Handle bonsai care actions"""
    
    child_name = api.get_child_name()
    
    try:
        if action == "show_bonsai_care":
            await api.speak(f"Hi {child_name}! Let me help you take great care of your bonsai!")
            await show_care_panel()
            tip = random.choice(GENERAL_TIPS)
            await api.speak(f"Here's a helpful tip: {tip}")
            return {"success": True, "message": "Bonsai care guide shown"}
            
        elif action == "watering_tips":
            tip = random.choice(WATERING_TIPS)
            await api.speak(f"Here's a watering tip, {child_name}: {tip}")
            
            # Check last watered date
            last_watered = api.get_data("last_watered")
            if last_watered:
                days_ago = (datetime.now() - datetime.fromisoformat(last_watered)).days
                if days_ago > 3:
                    await api.speak(f"By the way, it's been {days_ago} days since you last watered. You might want to check the soil!")
            else:
                await api.speak("Don't forget to record when you water your bonsai!")
            
            return {"success": True}
            
        elif action == "trimming_tips":
            tip = random.choice(TRIMMING_TIPS)
            await api.speak(f"Here's a trimming tip: {tip}")
            
            # Add seasonal advice
            season = get_current_season()
            if season in SEASONAL_CARE:
                await api.speak(f"For {season}: {SEASONAL_CARE[season]}")
                
            return {"success": True}
            
        elif action == "set_reminder":
            await api.speak("I'll help you set up bonsai care reminders!")
            
            # Set default reminders
            api.set_data("water_reminder_days", 2)
            api.set_data("check_reminder_days", 7)
            next_water = datetime.now() + timedelta(days=2)
            api.set_data("next_water_reminder", next_water.isoformat())
            
            await api.speak(f"I've set reminders to check watering every 2 days and general care every week. Ask me to 'check my bonsai' anytime!")
            return {"success": True}
            
        elif action == "check_bonsai":
            await check_bonsai_status(child_name)
            return {"success": True}
            
        # UI Panel actions
        elif action == "record_watering":
            api.set_data("last_watered", datetime.now().isoformat())
            await api.speak("Great job watering your bonsai! I've recorded today's date.")
            return {"success": True}
            
        elif action == "record_trimming":
            api.set_data("last_trimmed", datetime.now().isoformat())
            await api.speak("Nice work trimming your bonsai! Recorded in your care log.")
            return {"success": True}
            
        elif action == "get_random_tip":
            all_tips = GENERAL_TIPS + WATERING_TIPS + TRIMMING_TIPS
            tip = random.choice(all_tips)
            await api.speak(f"Here's a bonsai tip: {tip}")
            return {"success": True}
            
    except Exception as e:
        await api.speak("Oops, something went wrong with the bonsai care tool!")
        return {"success": False, "error": str(e)}
    
    return {"success": False, "message": f"Unknown action: {action}"}

async def show_care_panel():
    """Display the bonsai care interface"""
    
    # Get care history
    last_watered = api.get_data("last_watered")
    last_trimmed = api.get_data("last_trimmed")
    
    watered_text = "Never recorded" if not last_watered else format_days_ago(last_watered)
    trimmed_text = "Never recorded" if not last_trimmed else format_days_ago(last_trimmed)
    
    care_html = f"""
    <div style="max-width: 400px; margin: 0 auto; padding: 20px; background: linear-gradient(135deg, #e8f5e8, #f0f8f0); border-radius: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
        <h2 style="text-align: center; color: #2d5a2d; margin-bottom: 20px;">🌿 Bonsai Care Helper 🌿</h2>
        
        <div style="background: white; padding: 15px; border-radius: 10px; margin: 10px 0; border-left: 4px solid #228B22;">
            <h3 style="color: #2d5a2d; margin: 0 0 10px 0;">📅 Care Log</h3>
            <p><strong>Last Watered:</strong> {watered_text}</p>
            <p><strong>Last Trimmed:</strong> {trimmed_text}</p>
        </div>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 15px 0;">
            <button onclick="recordWatering()" style="background: #4CAF50; color: white; border: none; padding: 10px; border-radius: 8px; cursor: pointer;">💧 Just Watered</button>
            <button onclick="recordTrimming()" style="background: #8BC34A; color: white; border: none; padding: 10px; border-radius: 8px; cursor: pointer;">✂️ Just Trimmed</button>
        </div>
        
        <div style="text-align: center; margin: 15px 0;">
            <button onclick="getRandomTip()" style="background: #2E7D32; color: white; border: none; padding: 12px 20px; border-radius: 8px; cursor: pointer; font-weight: bold;">🌱 Get Care Tip</button>
        </div>
        
        <div style="background: #f8f9fa; padding: 10px; border-radius: 8px; margin-top: 15px;">
            <p style="margin: 5px 0; font-size: 14px; color: #555;"><strong>Quick Tips:</strong></p>
            <p style="margin: 5px 0; font-size: 12px; color: #666;">• Check soil daily - should be slightly damp</p>
            <p style="margin: 5px 0; font-size: 12px; color: #666;">• Bright, indirect sunlight is best</p>
            <p style="margin: 5px 0; font-size: 12px; color: #666;">• Be patient - bonsai grow slowly!</p>
        </div>
    </div>
    """ + """
    <script>
        function recordWatering() {
            fetch('/api/extensions/bonsai_care_tool/action', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({action: 'record_watering'})
            });
        }
        
        function recordTrimming() {
            fetch('/api/extensions/bonsai_care_tool/action', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({action: 'record_trimming'})
            });
        }
        
        function getRandomTip() {
            fetch('/api/extensions/bonsai_care_tool/action', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({action: 'get_random_tip'})
            });
        }
    </script>
    """
    
    await api.show_panel(care_html, panel_id="bonsai_care")

async def check_bonsai_status(child_name):
    """Check and report on bonsai care status"""
    
    last_watered = api.get_data("last_watered")
    messages = []
    
    if not last_watered:
        messages.append("I don't have any watering records yet. Don't forget to water your bonsai regularly!")
    else:
        days_since_water = (datetime.now() - datetime.fromisoformat(last_watered)).days
        
        if days_since_water == 0:
            messages.append("Great! You watered your bonsai today. Perfect care!")
        elif days_since_water == 1:
            messages.append("You watered yesterday - check if the soil is still damp.")
        elif days_since_water <= 3:
            messages.append(f"It's been {days_since_water} days since watering. Time to check the soil!")
        else:
            messages.append(f"It's been {days_since_water} days since watering. Your bonsai might be getting thirsty!")
    
    # Add seasonal care reminder
    season = get_current_season()
    if season in SEASONAL_CARE:
        messages.append(f"Remember for {season}: {SEASONAL_CARE[season]}")
    
    # Share a random encouraging message
    encouraging = [
        "You're doing great caring for your bonsai!",
        "Bonsai care teaches patience and attention - you're learning valuable skills!",
        "Your bonsai is lucky to have someone who cares so much!",
        "Every day you care for your bonsai, you're helping it grow stronger!"
    ]
    messages.append(random.choice(encouraging))
    
    for message in messages:
        await api.speak(f"{child_name}, {message}")

def get_current_season():
    """Get the current season based on month"""
    month = datetime.now().month
    if month in [3, 4, 5]:
        return "spring"
    elif month in [6, 7, 8]:
        return "summer"
    elif month in [9, 10, 11]:
        return "fall"
    else:
        return "winter"

def format_days_ago(date_str):
    """Format a date as 'X days ago'"""
    try:
        date = datetime.fromisoformat(date_str)
        days = (datetime.now() - date).days
        
        if days == 0:
            return "Today"
        elif days == 1:
            return "Yesterday"
        else:
            return f"{days} days ago"
    except:
        return "Unknown date"

async def on_load():
    """Called when extension loads"""
    # Initialize default data if needed
    if not api.get_data("initialized"):
        api.set_data("initialized", True)
        api.set_data("care_level", "beginner")