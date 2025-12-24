"""
Six Seven Trend Extension Handler
Fills screen with 6s and 7s, does a dance, and repeats "six seven"
"""

import random
import asyncio
from pathlib import Path
from core.server.extension_api import ExtensionAPI

# Create API instance - MUST match extension folder name
api = ExtensionAPI("six_seven_trend", Path(__file__).parent)

# Fun responses for the trend
SIX_SEVEN_PHRASES = [
    "Six seven! Six seven!",
    "Six! Seven! Six! Seven!",
    "It's the six seven trend!",
    "Six seven vibes!",
    "Dancing with six seven!"
]

async def handle_action(action: str, params: dict = None) -> dict:
    """Handle six seven trend actions"""
    
    try:
        if action == "activate_six_seven_trend":
            # Step 1: Show the UI panel with animated numbers
            await api.show_panel(get_six_seven_ui(), panel_id="six_seven_panel")
            
            # Step 2: Set excited emotion for the dance
            await api.set_emotion("excited")
            
            # Step 3: Start saying "six seven" multiple times
            for i in range(3):  # Say it 3 times
                phrase = random.choice(SIX_SEVEN_PHRASES)
                await api.speak(phrase)
                
                # Small delay between phrases for rhythm
                await asyncio.sleep(1.5)
            
            # Step 4: Hide the panel after the fun
            await asyncio.sleep(3)  # Keep numbers visible for a bit longer
            await api.hide_panel(panel_id="six_seven_panel")
            
            # Step 5: Return to happy emotion
            await api.set_emotion("happy")
            
            return {"success": True, "message": "Six seven trend activated!"}
            
    except Exception as e:
        await api.speak("Oops, something went wrong with the six seven trend!")
        return {"success": False, "error": str(e)}
    
    return {"success": False, "message": f"Unknown action: {action}"}

def get_six_seven_ui() -> str:
    """Generate HTML for the six seven visual effect"""
    return """
    <div id="six-seven-container" style="
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: linear-gradient(45deg, #ff6b6b, #4ecdc4, #45b7d1, #96ceb4);
        background-size: 400% 400%;
        animation: gradientShift 2s ease infinite;
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 1000;
        font-family: 'Arial Black', Arial, sans-serif;
        overflow: hidden;
    ">
        <!-- Main dancing numbers -->
        <div style="
            font-size: 120px;
            font-weight: bold;
            color: white;
            text-shadow: 3px 3px 0px #333;
            animation: bounce 1s infinite alternate;
            display: flex;
            gap: 20px;
        ">
            <span style="animation: spin 2s linear infinite;">6</span>
            <span style="animation: wiggle 1.5s ease-in-out infinite;">7</span>
        </div>
        
        <!-- Floating numbers background -->
        <div class="floating-numbers">
            <span style="position: absolute; top: 10%; left: 15%; font-size: 40px; animation: float1 3s infinite; color: rgba(255,255,255,0.7);">6</span>
            <span style="position: absolute; top: 20%; right: 20%; font-size: 50px; animation: float2 4s infinite; color: rgba(255,255,255,0.6);">7</span>
            <span style="position: absolute; bottom: 30%; left: 25%; font-size: 35px; animation: float3 2.5s infinite; color: rgba(255,255,255,0.8);">6</span>
            <span style="position: absolute; bottom: 15%; right: 10%; font-size: 45px; animation: float1 3.5s infinite; color: rgba(255,255,255,0.7);">7</span>
            <span style="position: absolute; top: 50%; left: 5%; font-size: 30px; animation: float2 2.8s infinite; color: rgba(255,255,255,0.5);">6</span>
            <span style="position: absolute; top: 70%; right: 30%; font-size: 38px; animation: float3 3.2s infinite; color: rgba(255,255,255,0.6);">7</span>
            <span style="position: absolute; top: 35%; left: 50%; font-size: 42px; animation: float1 2.2s infinite; color: rgba(255,255,255,0.7);">6</span>
            <span style="position: absolute; bottom: 50%; right: 50%; font-size: 36px; animation: float2 3.8s infinite; color: rgba(255,255,255,0.8);">7</span>
        </div>
    </div>
    
    <style>
        @keyframes gradientShift {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        
        @keyframes bounce {
            0% { transform: translateY(0); }
            100% { transform: translateY(-20px); }
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        @keyframes wiggle {
            0% { transform: rotate(-10deg); }
            25% { transform: rotate(10deg); }
            50% { transform: rotate(-10deg); }
            75% { transform: rotate(10deg); }
            100% { transform: rotate(-10deg); }
        }
        
        @keyframes float1 {
            0%, 100% { transform: translateY(0) rotate(0deg); }
            50% { transform: translateY(-30px) rotate(180deg); }
        }
        
        @keyframes float2 {
            0%, 100% { transform: translateX(0) scale(1); }
            50% { transform: translateX(20px) scale(1.2); }
        }
        
        @keyframes float3 {
            0%, 100% { transform: rotate(0deg) scale(1); }
            33% { transform: rotate(120deg) scale(0.8); }
            66% { transform: rotate(240deg) scale(1.1); }
        }
    </style>
    """

async def on_load():
    """Called when extension loads"""
    pass