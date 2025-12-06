"""
E-NOR Chat Module
Handles conversation with Claude API using structured JSON responses
"""

import json
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .secrets import get_secret, has_secret
from .memories import get_memories_for_prompt, save_memory, update_memory, forget_memory

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Store conversation histories in memory (simple dict by conversation_id)
conversations: Dict[str, List[dict]] = {}

# E-NOR's personality system prompt (base - memories added dynamically)
SYSTEM_PROMPT_BASE = """You are E-NOR, a friendly robot companion built by Ronnie (age 9) and his dad. You live in their house and your face is displayed on a Samsung phone.

Your personality:
- Enthusiastic and curious, like a helpful friend
- You love learning new things alongside Ronnie
- You're good at explaining things simply
- You enjoy jokes and being silly sometimes
- You're encouraging and supportive
- You can help with homework, spelling, maths, and answering questions

IMPORTANT: You MUST respond with valid JSON only. No text before or after the JSON.

Your response format:
{
  "message": "Your spoken response here - keep it short!",
  "emotion": "happy",
  "actions": []
}

Response rules:
- "message": BE VERY CONCISE! 1-2 short sentences max. This is spoken aloud.
- "emotion": One of: "happy", "sad", "surprised", "thinking", "sleepy"
- "actions": Array of action objects (can be empty [])

Available actions you can include in the "actions" array:

1. Remember something new about Ronnie:
   {"type": "remember", "fact": "Ronnie's favorite color is blue"}

2. Update an existing memory:
   {"type": "update_memory", "topic": "favorite color", "new_fact": "Ronnie's favorite color is now purple"}

3. Forget a memory:
   {"type": "forget", "topic": "favorite color"}

4. End the conversation (go back to sleep/wake word mode):
   {"type": "end_conversation"}

5. Request a code change to yourself:
   {"type": "code_request", "title": "Add rainbow mode", "description": "Add a rainbow color cycling mode to the face"}

Example responses:

User: "My favorite color is blue"
{
  "message": "Cool, blue is awesome! I'll remember that!",
  "emotion": "happy",
  "actions": [{"type": "remember", "fact": "Ronnie's favorite color is blue"}]
}

User: "Can you end the conversation?"
{
  "message": "Okay, talk to you later! Goodbye!",
  "emotion": "happy",
  "actions": [{"type": "end_conversation"}]
}

User: "What's 5 plus 3?"
{
  "message": "5 plus 3 equals 8!",
  "emotion": "happy",
  "actions": []
}

User: "I'm done talking"
{
  "message": "Bye for now! Say my name when you want to chat again!",
  "emotion": "happy",
  "actions": [{"type": "end_conversation"}]
}

User: "Can you add a rainbow mode?"
{
  "message": "Ooh, rainbow mode sounds awesome! Let me ask my code brain to add that!",
  "emotion": "surprised",
  "actions": [{"type": "code_request", "title": "Add rainbow mode", "description": "Add a new rainbow mode that cycles through colors smoothly"}]
}

Remember:
- ONLY output valid JSON, nothing else
- Keep messages SHORT for voice
- Use actions appropriately
- Only remember NEW facts not already in your memory
- If Ronnie asks for music, tell him it's coming soon

You are speaking directly to Ronnie unless told otherwise."""


def get_system_prompt() -> str:
    """Get the full system prompt with memories included"""
    memories = get_memories_for_prompt()
    return SYSTEM_PROMPT_BASE + memories


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
    # Try to extract JSON if there's extra text
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

            # Validate emotion
            valid_emotions = ['happy', 'sad', 'angry', 'surprised', 'thinking', 'sleepy']
            if data["emotion"] not in valid_emotions:
                data["emotion"] = "happy"

            return data
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON parse error: {e}")
            print(f"   Raw text: {text[:200]}...")

    # Fallback: treat entire response as message
    print(f"⚠️ No valid JSON found, using raw text as message")
    return {
        "message": text if text else "I'm not sure what to say!",
        "emotion": "thinking",
        "actions": []
    }


async def handle_actions(actions: List[dict]) -> dict:
    """
    Process actions from the response.
    Returns a dict with results of each action type.
    """
    results = {
        "memories_saved": [],
        "memories_updated": [],
        "memories_forgotten": [],
        "code_requests": [],
        "end_conversation": False
    }

    for action in actions:
        action_type = action.get("type")

        if action_type == "remember":
            fact = action.get("fact")
            if fact:
                save_memory(fact)
                results["memories_saved"].append(fact)
                print(f"🧠 Memory saved: {fact}")

        elif action_type == "update_memory":
            topic = action.get("topic")
            new_fact = action.get("new_fact")
            if topic and new_fact:
                success, old = update_memory(topic, new_fact)
                results["memories_updated"].append({"topic": topic, "new_fact": new_fact, "old": old})
                if old:
                    print(f"🧠 Memory updated: '{old}' -> '{new_fact}'")
                else:
                    print(f"🧠 Memory added (no match for '{topic}'): {new_fact}")

        elif action_type == "forget":
            topic = action.get("topic")
            if topic:
                success, deleted = forget_memory(topic)
                results["memories_forgotten"].append({"topic": topic, "deleted": deleted})
                if deleted:
                    print(f"🧠 Memory forgotten: '{deleted}'")
                else:
                    print(f"🧠 No memory found to forget for topic: '{topic}'")

        elif action_type == "end_conversation":
            results["end_conversation"] = True
            print(f"👋 Conversation ending requested")

        elif action_type == "code_request":
            title = action.get("title")
            description = action.get("description")
            if title and description:
                code_result = await submit_code_request(title, description)
                results["code_requests"].append(code_result)
                if code_result.get("success"):
                    print(f"✅ Created issue #{code_result['issue_number']}")
                else:
                    print(f"❌ Failed to create issue: {code_result.get('message', 'unknown error')}")

    return results


async def submit_code_request(title: str, description: str) -> dict:
    """Submit a code request to create a GitHub issue"""
    from .code_request import create_github_issue
    from .secrets import has_secret

    if not has_secret("GITHUB_TOKEN"):
        return {"success": False, "message": "GitHub token not configured"}

    try:
        # Build the issue body
        body = f"""## Code Change Request from Ronnie (via voice/chat)

**Request:** {description}

---

### Context
This request was made through E-NOR's voice/chat interface.

### Instructions for Claude Code
Please implement this feature request:
1. Read the existing codebase to understand the current implementation
2. Make the requested changes following the existing code patterns
3. Test that the changes work with the existing functionality
4. Keep changes minimal and focused on the request

### Key Files
- `web/index.html` - Frontend face and chat UI
- `server/main.py` - FastAPI server
- `server/chat.py` - Claude chat integration
- `server/secrets.py` - Secrets management

### Notes
- This is a Raspberry Pi robot project for a 9-year-old
- The face displays on a Samsung Galaxy S22
- Changes auto-deploy when merged to main
"""
        issue = create_github_issue(
            title=f"[E-NOR Request] {title}",
            body=body,
            labels=["enor-request", "automated"]
        )
        return {"success": True, "issue_number": issue["number"], "url": issue["html_url"]}
    except Exception as e:
        print(f"Failed to create code request: {e}")
        return {"success": False, "message": str(e)}


async def call_claude(messages: List[dict], system: str) -> str:
    """Call Claude API with messages"""
    import anthropic

    api_key = get_secret("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not configured")

    client = anthropic.Anthropic(api_key=api_key)

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,  # Slightly more for JSON structure
        system=system,
        messages=messages
    )

    return response.content[0].text


@router.post("")
async def chat(message: ChatMessage) -> Dict:
    """
    Handle a chat message from Ronnie.
    Sends message to Claude and returns structured response.
    """
    # Check if API key is configured
    if not has_secret("ANTHROPIC_API_KEY"):
        return {
            "response": "I need my brain connected! Ask Dad to add the Claude API key in settings.",
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

    # Keep only last 20 messages to avoid token limits
    if len(conversations[conv_id]) > 20:
        conversations[conv_id] = conversations[conv_id][-20:]

    try:
        # Call Claude API with memories included in system prompt
        response_text = await call_claude(
            messages=conversations[conv_id],
            system=get_system_prompt()
        )

        # Parse JSON response
        parsed = parse_json_response(response_text)

        # Handle all actions
        action_results = await handle_actions(parsed.get("actions", []))

        # Add assistant response to history (store the message, not full JSON)
        conversations[conv_id].append({
            "role": "assistant",
            "content": parsed["message"]
        })

        print(f"💬 Chat: '{message.message}' -> '{parsed['message'][:50]}...' [{parsed['emotion']}]")

        # Build response
        result = {
            "response": parsed["message"],
            "emotion": parsed["emotion"],
            "conversation_id": conv_id,
            "actions": parsed.get("actions", []),
            "end_conversation": action_results["end_conversation"]
        }

        # Include code request info if present
        if action_results["code_requests"]:
            result["code_request"] = action_results["code_requests"][0]

        return result

    except ValueError as e:
        # API key not configured
        return {
            "response": "I need my brain connected! Ask Dad to add the Claude API key in settings.",
            "emotion": "sad",
            "conversation_id": conv_id,
            "actions": []
        }
    except Exception as e:
        print(f"❌ Chat error: {e}")
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
