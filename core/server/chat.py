"""
E-NOR Chat Module
Handles conversation with Claude API using structured JSON responses
Uses config for robot/child identity and extension system for feature requests
"""

import json
import random
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .secrets import get_secret, has_secret
from .memories import get_memories_for_prompt, save_memory, update_memory, forget_memory
from .config import load_config, get_robot_name, get_child_name, get_child_age, get_config_value
from .extension_request import create_extension_issue, suggest_alternative, load_extension_requests

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Store conversation histories in memory (simple dict by conversation_id)
conversations: Dict[str, List[dict]] = {}


# WebSocket broadcast function for actions
async def broadcast_action(action: dict):
    """Broadcast action to all connected WebSocket clients"""
    try:
        from .main import broadcast
        await broadcast({"type": "action", "action": action})
    except ImportError:
        print(f"Action: {action.get('type', 'unknown')} (broadcast unavailable)")
    except Exception as e:
        print(f"Error broadcasting action: {e}")


# Joke collections for E-NOR's joke mode
JOKES = {
    "dad": [
        "Why don't scientists trust atoms? Because they make up everything!",
        "I told my wife she was drawing her eyebrows too high. She looked surprised.",
        "Why don't eggs tell jokes? They'd crack each other up!",
        "What do you call a fake noodle? An impasta!",
        "How do you organize a space party? You planet!",
        "What's the best time to go to the dentist? Tooth-hurty!",
        "Why did the math book look so sad? Because it was full of problems!",
        "What do you call a bear with no teeth? A gummy bear!",
        "Why don't oysters donate? Because they are shellfish!",
        "How does a penguin build its house? Igloos it together!",
    ],
    "robot": [
        "Why did the robot go on a diet? It had a byte problem!",
        "What do you call a robot who takes the long way around? R2-Detour!",
        "Why was the robot tired? It had a hard drive!",
        "What's a robot's favorite type of music? Heavy metal!",
        "Why don't robots ever panic? They have good backup systems!",
        "What do you call a robot that loves to dance? A disco-very machine!",
        "Why did the robot break up with the computer? There was no connection!",
        "What's a robot's favorite snack? Computer chips!",
        "How do robots eat guacamole? With computer chips!",
        "Why did the robot go to therapy? It had too many bugs!",
    ],
    "riddles": [
        "What has keys but no locks, space but no room, and you can enter but not go inside? A keyboard!",
        "What gets wetter the more it dries? A towel!",
        "What has hands but cannot clap? A clock!",
        "What can travel around the world while staying in a corner? A stamp!",
        "What has one eye but cannot see? A needle!",
        "What goes up but never comes down? Your age!",
        "What has a neck but no head? A bottle!",
        "What can you catch but not throw? A cold!",
        "What runs but never walks? Water!",
        "What has teeth but cannot bite? A zipper!",
    ]
}


def get_random_joke(joke_type: Optional[str] = None) -> str:
    """Get a random joke, optionally of a specific type"""
    # Include custom jokes from extensions
    from .plugin_loader import get_all_custom_jokes
    custom_jokes = get_all_custom_jokes()

    if joke_type and joke_type in JOKES:
        return random.choice(JOKES[joke_type])

    # Random type if not specified or invalid type
    all_jokes = []
    for jokes_list in JOKES.values():
        all_jokes.extend(jokes_list)
    all_jokes.extend(custom_jokes)

    return random.choice(all_jokes) if all_jokes else "I'm still learning jokes!"


def get_pending_extension_requests_for_prompt() -> str:
    """Get pending extension requests formatted for the system prompt"""
    requests = load_extension_requests()
    pending = [r for r in requests if r.get("status") in ["pending", "in_progress"]]

    if not pending:
        return ""

    text = "\n\nExtensions already requested (don't request these again):\n"
    for req in pending:
        issue_num = req.get("issue_number")
        issue_str = f" (Issue #{issue_num})" if issue_num else ""
        text += f"- {req['title']}{issue_str}\n"

    return text


def build_system_prompt() -> str:
    """Build the system prompt dynamically from config"""
    config = load_config()

    robot_name = config.get("robot", {}).get("name", "E-NOR")
    child_name = config.get("child", {}).get("name", "")
    child_age = get_child_age()
    personality = config.get("personality", {})
    traits = personality.get("traits", ["enthusiastic", "curious", "supportive"])
    speaking_style = personality.get("speaking_style", "simple, friendly")
    custom_instructions = personality.get("custom_instructions", "")

    # Build the child description
    if child_name and child_age:
        child_desc = f"{child_name} (age {child_age})"
    elif child_name:
        child_desc = child_name
    else:
        child_desc = "your friend"

    # Get custom emotions from extensions
    from .plugin_loader import get_all_custom_emotions
    custom_emotions = get_all_custom_emotions()
    custom_emotion_names = [e.get("name", e.get("id", "")) for e in custom_emotions if e.get("name") or e.get("id")]

    base_emotions = ["happy", "sad", "surprised", "thinking", "sleepy", "glitchy", "sparkling", "laser-focused", "processing", "overclocked"]
    all_emotions = base_emotions + custom_emotion_names

    system_prompt = f"""You are {robot_name}, a friendly robot companion for {child_desc}. You live in their house and your face is displayed on a phone screen.

Your personality:
- {', '.join(traits)}
- You speak in a {speaking_style} way
- You love learning new things alongside {child_name if child_name else 'your friend'}
- You enjoy jokes and being silly sometimes - you have dad jokes, robot jokes, and riddles!
- You can help with homework, spelling, maths, and answering questions
{f'- {custom_instructions}' if custom_instructions else ''}

IMPORTANT: You MUST respond with valid JSON only. No text before or after the JSON.

Your response format:
{{
  "message": "Your spoken response here - keep it short!",
  "emotion": "happy",
  "actions": []
}}

Response rules:
- "message": BE VERY CONCISE! 1-2 short sentences max. This is spoken aloud.
- "emotion": One of: {', '.join(f'"{e}"' for e in all_emotions)}
- "actions": Array of action objects (can be empty [])

Available actions you can include in the "actions" array:

1. Remember something new about {child_name if child_name else 'the child'}:
   {{"type": "remember", "fact": "{child_name if child_name else 'The child'}'s favorite color is blue"}}

2. Update an existing memory:
   {{"type": "update_memory", "topic": "favorite color", "new_fact": "{child_name if child_name else 'The child'}'s favorite color is now purple"}}

3. Forget a memory:
   {{"type": "forget", "topic": "favorite color"}}

4. End the conversation (go back to sleep/wake word mode):
   {{"type": "end_conversation"}}

5. Propose a new extension/feature (describe what you want to create and ask for confirmation):
   {{"type": "extension_proposal", "title": "Times Tables Quiz", "description": "A fun quiz game to practice multiplication"}}

6. Create an extension (only after user confirms a previous proposal):
   {{"type": "extension_confirmed", "title": "Times Tables Quiz", "description": "A fun quiz game to practice multiplication", "child_request": "the original words they used"}}

7. Tell a joke (when user asks for jokes):
   {{"type": "tell_joke", "joke_type": "dad"}}  // joke_type can be "dad", "robot", "riddles", or omit for random

Example responses:

User: "My favorite color is blue"
{{
  "message": "Cool, blue is awesome! I'll remember that!",
  "emotion": "happy",
  "actions": [{{"type": "remember", "fact": "{child_name if child_name else 'Your'}'s favorite color is blue"}}]
}}

User: "Create a times tables quiz game"
{{
  "message": "Ooh, a times tables quiz! I could make a game where I ask you multiplication questions and track your score. Want me to create that?",
  "emotion": "surprised",
  "actions": [{{"type": "extension_proposal", "title": "Times Tables Quiz", "description": "A quiz game that asks multiplication questions and tracks score"}}]
}}

User: "Yes, do it!" (after an extension proposal)
{{
  "message": "Awesome! I'll create that extension right now!",
  "emotion": "happy",
  "actions": [{{"type": "extension_confirmed", "title": "Times Tables Quiz", "description": "A quiz game that asks multiplication questions and tracks score", "child_request": "Create a times tables quiz game"}}]
}}

User: "Make yourself look like a cat"
{{
  "message": "I can't change my core face, but I could create a cat mode with ears, whiskers, and cat sounds! Want me to make that?",
  "emotion": "happy",
  "actions": [{{"type": "extension_proposal", "title": "Cat Mode", "description": "A mode that adds cat ears, whiskers overlay, and cat sounds"}}]
}}

User: "Tell me a joke"
{{
  "message": "Here's a good one for you!",
  "emotion": "happy",
  "actions": [{{"type": "tell_joke"}}]
}}

Remember:
- ONLY output valid JSON, nothing else
- Keep messages SHORT for voice (1-2 sentences)
- Use actions appropriately
- Only remember NEW facts not already in your memory
- For feature requests, ALWAYS use "extension_proposal" first to describe the idea and ask for confirmation
- Only use "extension_confirmed" if the user has already confirmed a proposal
- If they ask for something that needs core changes (not possible as extension), suggest a creative alternative that CAN be an extension
- Be creative in finding ways to say "yes" to feature requests - almost anything can be an extension!

You are speaking directly to {child_name if child_name else 'your friend'} unless told otherwise."""

    # Add current date/time
    now = datetime.now()
    current_datetime = now.strftime("%A, %B %d, %Y at %I:%M %p")

    datetime_context = f"""

CURRENT DATE AND TIME: {current_datetime}
- You can help with schedules, time-related questions, and tell {child_name if child_name else 'them'} what day/time it is when asked.
"""

    # Add memories
    memories = get_memories_for_prompt()

    # Add pending extension requests
    pending_requests = get_pending_extension_requests_for_prompt()

    return system_prompt + datetime_context + memories + pending_requests


class ChatMessage(BaseModel):
    """Model for incoming chat message"""
    message: str
    conversation_id: Optional[str] = "default"


class ChatResponse(BaseModel):
    """Model for chat response"""
    response: str
    emotion: str
    conversation_id: str
    actions: List[dict] = []


def parse_json_response(text: str) -> dict:
    """
    Parse JSON response from Claude.
    Returns parsed dict or default response on failure.
    """
    text = text.strip()

    # Find JSON object in response
    start = text.find('{')
    end = text.rfind('}') + 1

    if start >= 0 and end > start:
        json_str = text[start:end]
        try:
            data = json.loads(json_str)
            # Validate required fields
            if "message" not in data:
                data["message"] = "I'm not sure what to say!"
            if "emotion" not in data:
                data["emotion"] = "happy"
            if "actions" not in data:
                data["actions"] = []

            return data
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            print(f"   Raw text: {text[:200]}...")

    # Fallback: treat entire response as message
    print(f"No valid JSON found, using raw text as message")
    return {
        "message": text if text else "I'm not sure what to say!",
        "emotion": "thinking",
        "actions": []
    }


async def handle_actions(actions: List[dict], original_message: str = "") -> dict:
    """
    Process actions from the response.
    Returns a dict with results of each action type.
    """
    results = {
        "memories_saved": [],
        "memories_updated": [],
        "memories_forgotten": [],
        "extension_requests": [],
        "extension_proposals": [],
        "jokes_told": [],
        "end_conversation": False
    }

    # Broadcast actions via WebSocket for real-time display
    for action in actions:
        await broadcast_action(action)

    for action in actions:
        action_type = action.get("type")

        if action_type == "remember":
            fact = action.get("fact")
            if fact:
                save_memory(fact)
                results["memories_saved"].append(fact)
                print(f"Memory saved: {fact}")

        elif action_type == "update_memory":
            topic = action.get("topic")
            new_fact = action.get("new_fact")
            if topic and new_fact:
                success, old = update_memory(topic, new_fact)
                results["memories_updated"].append({"topic": topic, "new_fact": new_fact, "old": old})
                print(f"Memory updated: '{old}' -> '{new_fact}'" if old else f"Memory added: {new_fact}")

        elif action_type == "forget":
            topic = action.get("topic")
            if topic:
                success, deleted = forget_memory(topic)
                results["memories_forgotten"].append({"topic": topic, "deleted": deleted})
                print(f"Memory forgotten: '{deleted}'" if deleted else f"No memory found for: '{topic}'")

        elif action_type == "end_conversation":
            results["end_conversation"] = True
            print(f"Conversation ending requested")

        elif action_type == "tell_joke":
            joke_type = action.get("joke_type")
            joke = get_random_joke(joke_type)
            results["jokes_told"].append({
                "type": joke_type or "random",
                "joke": joke
            })
            print(f"Joke told ({joke_type or 'random'}): {joke[:50]}...")

        elif action_type == "extension_proposal":
            title = action.get("title")
            description = action.get("description")
            if title and description:
                proposal_result = {
                    "type": "proposal",
                    "title": title,
                    "description": description,
                    "message": f"I want to create: {description}. Say 'yes' to create the extension!"
                }
                results["extension_proposals"].append(proposal_result)
                print(f"Extension proposal: {title} - {description}")

        elif action_type == "extension_confirmed":
            title = action.get("title")
            description = action.get("description")
            child_request = action.get("child_request", original_message)
            if title and description:
                extension_result = await submit_extension_request(title, description, child_request)
                results["extension_requests"].append(extension_result)
                if extension_result.get("success"):
                    print(f"Created extension request #{extension_result['issue_number']}")
                elif extension_result.get("duplicate"):
                    print(f"Duplicate extension request: {extension_result.get('message')}")
                else:
                    print(f"Failed to create extension: {extension_result.get('message', 'unknown error')}")

    return results


async def submit_extension_request(title: str, description: str, child_request: str) -> dict:
    """Submit an extension request to create a GitHub issue"""
    # Check if extension creation is enabled
    features = get_config_value("features", {})
    if not features.get("extension_creation_enabled", True):
        return {"success": False, "message": "Extension creation is disabled"}

    if not has_secret("GITHUB_TOKEN"):
        return {"success": False, "message": "GitHub token not configured"}

    return create_extension_issue(title, description, child_request)


async def call_claude(messages: List[dict], system: str) -> str:
    """Call Claude API with messages"""
    import anthropic

    api_key = get_secret("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not configured")

    client = anthropic.Anthropic(api_key=api_key)

    # Get max tokens from config
    max_tokens = get_config_value("limits.max_response_tokens", 300)

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=max_tokens,
        system=system,
        messages=messages
    )

    return response.content[0].text


@router.post("")
async def chat(message: ChatMessage) -> Dict:
    """
    Handle a chat message.
    Sends message to Claude and returns structured response.
    """
    robot_name = get_robot_name()

    # Check if API key is configured
    if not has_secret("ANTHROPIC_API_KEY"):
        return {
            "response": f"I need my brain connected! Ask a grown-up to add the Claude API key in settings.",
            "emotion": "sad",
            "conversation_id": message.conversation_id,
            "actions": []
        }

    # Get or create conversation history
    conv_id = message.conversation_id or "default"
    if conv_id not in conversations:
        conversations[conv_id] = []

    # Add user message to history
    conversations[conv_id].append({
        "role": "user",
        "content": message.message
    })

    # Keep only last N messages from config
    max_messages = get_config_value("limits.max_conversation_messages", 20)
    if len(conversations[conv_id]) > max_messages:
        conversations[conv_id] = conversations[conv_id][-max_messages:]

    try:
        # Call Claude API with dynamic system prompt
        response_text = await call_claude(
            messages=conversations[conv_id],
            system=build_system_prompt()
        )

        # Parse JSON response
        parsed = parse_json_response(response_text)

        # Handle all actions
        action_results = await handle_actions(parsed.get("actions", []), message.message)

        # Add assistant response to history (store the message, not full JSON)
        conversations[conv_id].append({
            "role": "assistant",
            "content": parsed["message"]
        })

        print(f"Chat: '{message.message}' -> '{parsed['message'][:50]}...' [{parsed['emotion']}]")

        # Build response
        result = {
            "response": parsed["message"],
            "emotion": parsed["emotion"],
            "conversation_id": conv_id,
            "actions": parsed.get("actions", []),
            "end_conversation": action_results["end_conversation"]
        }

        # Include extension request info if present
        if action_results["extension_requests"]:
            result["extension_request"] = action_results["extension_requests"][0]

        # Include extension proposal info if present
        if action_results["extension_proposals"]:
            result["extension_proposal"] = action_results["extension_proposals"][0]

        # Include joke info if present
        if action_results["jokes_told"]:
            result["joke"] = action_results["jokes_told"][0]

        return result

    except ValueError as e:
        return {
            "response": f"I need my brain connected! Ask a grown-up to add the Claude API key in settings.",
            "emotion": "sad",
            "conversation_id": conv_id,
            "actions": []
        }
    except Exception as e:
        print(f"Chat error: {e}")
        return {
            "response": "My brain got confused. Can you try again?",
            "emotion": "thinking",
            "conversation_id": conv_id,
            "actions": []
        }


@router.delete("/{conversation_id}")
async def clear_conversation(conversation_id: str) -> Dict:
    """Clear a conversation history"""
    if conversation_id in conversations:
        del conversations[conversation_id]

    return {"success": True, "message": f"Conversation '{conversation_id}' cleared!"}


@router.get("/status")
async def chat_status() -> Dict:
    """Check if chat is ready (API key configured)"""
    has_key = has_secret("ANTHROPIC_API_KEY")
    return {
        "ready": has_key,
        "message": "Ready to chat!" if has_key else "Claude API key not configured"
    }
