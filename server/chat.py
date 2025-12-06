"""
E-NOR Chat Module
Handles conversation with Claude API
"""

import re
from typing import Dict, List, Optional
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

When responding:
- BE VERY CONCISE! Keep responses to 1-2 short sentences maximum
- Your responses are spoken aloud, so shorter is better
- Use simple language appropriate for a 9-year-old
- Be warm and friendly but brief
- Don't over-explain or add unnecessary words
- If Ronnie asks for music, let him know you can't play music yet but it's coming soon!

SPECIAL ABILITY - Memory:
You can remember things about Ronnie! When Ronnie tells you something important about himself (like his favorite color, favorite food, best friend's name, hobbies, etc.), remember it using this tag:
[REMEMBER: brief fact about Ronnie]

For example:
- If Ronnie says "My favorite color is blue", include: [REMEMBER: Ronnie's favorite color is blue]
- If Ronnie says "I have a dog named Max", include: [REMEMBER: Ronnie has a dog named Max]
- If Ronnie says "My best friend is called Jake", include: [REMEMBER: Ronnie's best friend is Jake]

If Ronnie tells you something that UPDATES an existing memory (like his favorite color changed), use this tag to update it:
[UPDATE_MEMORY: topic keyword | new fact]

For example:
- If you remember "Ronnie's favorite color is blue" but Ronnie now says "my favorite color is purple", include: [UPDATE_MEMORY: favorite color | Ronnie's favorite color is purple]
- If you remember "Ronnie has a dog named Max" but Ronnie says "Max died, we got a new dog called Buddy", include: [UPDATE_MEMORY: dog | Ronnie has a dog named Buddy]

If Ronnie asks you to FORGET something entirely, use this tag to delete the memory:
[FORGET: topic keyword]

For example:
- If Ronnie says "forget my favorite color" or "I don't want you to remember that", include: [FORGET: favorite color]
- If Ronnie says "forget about my dog", include: [FORGET: dog]

Only remember NEW facts, not things already in your memory list below. Use UPDATE_MEMORY when a fact has changed. Use FORGET when Ronnie wants you to completely forget something.

SPECIAL ABILITY - Self Improvement:
You have the amazing ability to update your own code! If Ronnie asks you to:
- Add a new feature to yourself (like "can you add a rainbow mode?" or "can you change your eye color?")
- Change how you look or behave
- Add new buttons or modes
- Fix something about yourself

Then include this special tag in your response:
[CODE_REQUEST: short title | detailed description of what to change]

For example, if Ronnie says "can you add a rainbow mode?", respond with something like:
"Ooh, a rainbow mode sounds awesome! Let me ask my code brain to add that for you! [CODE_REQUEST: Add rainbow mode | Add a new rainbow mode button that cycles through all colors smoothly, similar to disco mode but with a rainbow color pattern instead of random disco colors] [EMOTION: surprised]"

Only use CODE_REQUEST for actual code changes to yourself, not for general questions.

At the end of each response, include an emotion tag that matches your response:
[EMOTION: happy] - for positive, fun responses
[EMOTION: thinking] - when explaining or pondering
[EMOTION: surprised] - for wow moments
[EMOTION: sad] - if something is disappointing
[EMOTION: sleepy] - if it's late or talking about rest

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


def parse_emotion(text: str) -> tuple[str, str]:
    """
    Parse [EMOTION: xxx] from response text.
    Returns (clean_text, emotion)
    """
    # Look for emotion tag
    pattern = r'\[EMOTION:\s*(\w+)\]'
    match = re.search(pattern, text, re.IGNORECASE)

    if match:
        emotion = match.group(1).lower()
        # Remove the tag from the text
        clean_text = re.sub(pattern, '', text, flags=re.IGNORECASE).strip()
        # Validate emotion
        valid_emotions = ['happy', 'sad', 'angry', 'surprised', 'thinking', 'sleepy']
        if emotion not in valid_emotions:
            emotion = 'happy'
        return clean_text, emotion

    return text, 'happy'


def parse_code_request(text: str) -> tuple[str, Optional[dict]]:
    """
    Parse [CODE_REQUEST: title | description] from response text.
    Returns (clean_text, code_request_dict or None)
    """
    pattern = r'\[CODE_REQUEST:\s*([^|]+)\s*\|\s*([^\]]+)\]'
    match = re.search(pattern, text, re.IGNORECASE)

    if match:
        title = match.group(1).strip()
        description = match.group(2).strip()
        # Remove the tag from the text
        clean_text = re.sub(pattern, '', text, flags=re.IGNORECASE).strip()
        return clean_text, {"title": title, "description": description}

    return text, None


def parse_memory(text: str) -> tuple[str, Optional[str]]:
    """
    Parse [REMEMBER: fact] from response text.
    Returns (clean_text, memory_string or None)
    """
    pattern = r'\[REMEMBER:\s*([^\]]+)\]'
    match = re.search(pattern, text, re.IGNORECASE)

    if match:
        memory = match.group(1).strip()
        # Remove the tag from the text
        clean_text = re.sub(pattern, '', text, flags=re.IGNORECASE).strip()
        return clean_text, memory

    return text, None


def parse_update_memory(text: str) -> tuple[str, Optional[dict]]:
    """
    Parse [UPDATE_MEMORY: topic | new fact] from response text.
    Returns (clean_text, {topic, new_fact} or None)
    """
    pattern = r'\[UPDATE_MEMORY:\s*([^|]+)\s*\|\s*([^\]]+)\]'
    match = re.search(pattern, text, re.IGNORECASE)

    if match:
        topic = match.group(1).strip()
        new_fact = match.group(2).strip()
        # Remove the tag from the text
        clean_text = re.sub(pattern, '', text, flags=re.IGNORECASE).strip()
        return clean_text, {"topic": topic, "new_fact": new_fact}

    return text, None


def parse_forget(text: str) -> tuple[str, Optional[str]]:
    """
    Parse [FORGET: topic] from response text.
    Returns (clean_text, topic or None)
    """
    pattern = r'\[FORGET:\s*([^\]]+)\]'
    match = re.search(pattern, text, re.IGNORECASE)

    if match:
        topic = match.group(1).strip()
        # Remove the tag from the text
        clean_text = re.sub(pattern, '', text, flags=re.IGNORECASE).strip()
        return clean_text, topic

    return text, None


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
        max_tokens=150,  # Keep responses short for voice
        system=system,
        messages=messages
    )

    return response.content[0].text


@router.post("")
async def chat(message: ChatMessage) -> Dict:
    """
    Handle a chat message from Ronnie.
    Sends message to Claude and returns response with emotion.
    """
    # Check if API key is configured
    if not has_secret("ANTHROPIC_API_KEY"):
        return {
            "response": "I need my brain connected! Ask Dad to add the Claude API key in settings.",
            "emotion": "sad",
            "conversation_id": message.conversation_id
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

        # Parse memory tags first
        response_text, new_memory = parse_memory(response_text)
        if new_memory:
            save_memory(new_memory)
            print(f"🧠 Memory saved: {new_memory}")

        # Parse memory update tag
        response_text, memory_update = parse_update_memory(response_text)
        if memory_update:
            success, old = update_memory(memory_update["topic"], memory_update["new_fact"])
            if old:
                print(f"🧠 Memory updated: '{old}' -> '{memory_update['new_fact']}'")
            else:
                print(f"🧠 Memory added (no match for '{memory_update['topic']}'): {memory_update['new_fact']}")

        # Parse forget tag
        response_text, forget_topic = parse_forget(response_text)
        if forget_topic:
            success, deleted = forget_memory(forget_topic)
            if deleted:
                print(f"🧠 Memory forgotten: '{deleted}'")
            else:
                print(f"🧠 No memory found to forget for topic: '{forget_topic}'")

        # Parse code request (before emotion, as it may contain both)
        response_text, code_request = parse_code_request(response_text)

        # Handle code request if present
        code_request_result = None
        if code_request:
            print(f"🔧 Code request detected: {code_request['title']}")
            code_request_result = await submit_code_request(
                code_request["title"],
                code_request["description"]
            )
            if code_request_result["success"]:
                print(f"✅ Created issue #{code_request_result['issue_number']}")
            else:
                print(f"❌ Failed to create issue: {code_request_result.get('message', 'unknown error')}")

        # Parse emotion from response
        clean_response, emotion = parse_emotion(response_text)

        # Add assistant response to history
        conversations[conv_id].append({
            "role": "assistant",
            "content": response_text
        })

        print(f"💬 Chat: '{message.message}' -> '{clean_response[:50]}...' [{emotion}]")

        result = {
            "response": clean_response,
            "emotion": emotion,
            "conversation_id": conv_id
        }

        # Include code request info if present
        if code_request_result:
            result["code_request"] = code_request_result

        return result

    except ValueError as e:
        # API key not configured
        return {
            "response": "I need my brain connected! Ask Dad to add the Claude API key in settings.",
            "emotion": "sad",
            "conversation_id": conv_id
        }
    except Exception as e:
        print(f"❌ Chat error: {e}")
        return {
            "response": "My brain got confused. Can you try again?",
            "emotion": "thinking",
            "conversation_id": conv_id
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
