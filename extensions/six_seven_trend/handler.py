"""
Six Seven Trend Extension Handler

When you say 'six seven,' the screen fills with sixes and sevens everywhere,
E-NOR does a fun dance move, and says 'six seven' repeatedly!
"""

import asyncio
import random
from pathlib import Path
from core.server.extension_api import ExtensionAPI

# Create API instance - MUST match extension folder name
api = ExtensionAPI("six_seven_trend", Path(__file__).parent)

# Six Seven responses
SIX_SEVEN_RESPONSES = [
    "Six seven!",
    "Six seven, six seven!",
    "Six! Seven!",
    "Six seven trend time!",
    "Six seven dance!"
]

async def handle_action(action: str, params: dict = None) -> dict:
    """Handle six seven trend actions"""

    if action == "start_six_seven_trend":
        # Clear any previous emergency stop flag so we can start fresh
        api.clear_stop_flag()

        # Start the six seven trend!
        await api.speak("Let's do the six seven trend!")
        
        # Set a fun energetic emotion
        await api.set_emotion("excited")
        
        # Show the sixes and sevens visual overlay
        await api.show_panel("""
        <div id="six-seven-overlay" style="
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: linear-gradient(45deg, #ff6b6b, #4ecdc4, #45b7d1, #f9ca24);
            background-size: 400% 400%;
            animation: gradientShift 3s ease infinite, dance 0.5s ease-in-out infinite alternate;
            z-index: 9999;
            pointer-events: none;
            overflow: hidden;
        ">
            <style>
                @keyframes gradientShift {
                    0% { background-position: 0% 50%; }
                    50% { background-position: 100% 50%; }
                    100% { background-position: 0% 50%; }
                }
                
                @keyframes dance {
                    0% { transform: scale(1) rotate(0deg); }
                    100% { transform: scale(1.05) rotate(2deg); }
                }
                
                @keyframes float {
                    0% { transform: translateY(100vh) rotate(0deg); }
                    100% { transform: translateY(-100px) rotate(360deg); }
                }
                
                .number {
                    position: absolute;
                    font-size: 4rem;
                    font-weight: bold;
                    color: white;
                    text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
                    animation: float linear infinite;
                    user-select: none;
                }
            </style>
            <!-- Generate lots of floating 6s and 7s -->
            <div class="number" style="left: 10%; animation-duration: 3s; animation-delay: 0s;">6</div>
            <div class="number" style="left: 20%; animation-duration: 4s; animation-delay: 0.5s;">7</div>
            <div class="number" style="left: 30%; animation-duration: 3.5s; animation-delay: 1s;">6</div>
            <div class="number" style="left: 40%; animation-duration: 4.5s; animation-delay: 1.5s;">7</div>
            <div class="number" style="left: 50%; animation-duration: 3s; animation-delay: 2s;">6</div>
            <div class="number" style="left: 60%; animation-duration: 4s; animation-delay: 2.5s;">7</div>
            <div class="number" style="left: 70%; animation-duration: 3.5s; animation-delay: 3s;">6</div>
            <div class="number" style="left: 80%; animation-duration: 4.5s; animation-delay: 3.5s;">7</div>
            <div class="number" style="left: 90%; animation-duration: 3s; animation-delay: 4s;">6</div>
            <div class="number" style="left: 15%; animation-duration: 4s; animation-delay: 4.5s;">7</div>
            <div class="number" style="left: 25%; animation-duration: 3.5s; animation-delay: 5s;">6</div>
            <div class="number" style="left: 35%; animation-duration: 4.5s; animation-delay: 5.5s;">7</div>
            <div class="number" style="left: 45%; animation-duration: 3s; animation-delay: 6s;">6</div>
            <div class="number" style="left: 55%; animation-duration: 4s; animation-delay: 6.5s;">7</div>
            <div class="number" style="left: 65%; animation-duration: 3.5s; animation-delay: 7s;">6</div>
            <div class="number" style="left: 75%; animation-duration: 4.5s; animation-delay: 7.5s;">7</div>
            <div class="number" style="left: 85%; animation-duration: 3s; animation-delay: 8s;">6</div>
            <div class="number" style="left: 95%; animation-duration: 4s; animation-delay: 8.5s;">7</div>
        </div>
        """, panel_id="six_seven_overlay", panel_type="action")
        
        # Store that we're active
        api.set_data("active", True)
        
        # Start the repeating six seven chant (async task)
        asyncio.create_task(six_seven_chant())
        
        return {"success": True, "message": "Six seven trend started!"}
    
    elif action == "stop_six_seven_trend":
        # Stop the trend
        await api.hide_panel(panel_id="six_seven_overlay")
        await api.set_emotion("happy")
        await api.speak("That was awesome! Six seven trend complete!")
        
        # Mark as inactive
        api.set_data("active", False)
        
        return {"success": True, "message": "Six seven trend stopped!"}
    
    return {"success": False, "message": f"Unknown action: {action}"}

async def six_seven_chant():
    """Keep saying 'six seven' repeatedly while the trend is active"""
    while api.get_data("active", False) and not api.is_stopped():
        # Wait a bit before next chant
        await asyncio.sleep(random.uniform(2, 4))

        # Check if still active AND not emergency stopped
        if api.get_data("active", False) and not api.is_stopped():
            response = random.choice(SIX_SEVEN_RESPONSES)
            await api.speak(response)
        else:
            # Stop was triggered, exit the loop
            print("[six_seven_trend] Chant loop stopped by emergency stop or deactivation")
            break

async def on_load():
    """Called when extension loads - reset state"""
    api.set_data("active", False)