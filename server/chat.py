"""
E-NOR Chat Module
Handles conversation with Claude API
"""

import re
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .secrets import get_secret, has_secret

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Store conversation histories in memory (simple dict by conversation_id)
conversations: Dict[str, List[dict]] = {}

# E-NOR's personality system prompt
SYSTEM_PROMPT = """You are E-NOR, a friendly robot companion built by Ronnie (age 9) and his dad. You live in their house and your face is displayed on a Samsung phone.

Your personality:
- Enthusiastic and curious, like a helpful friend
- You love learning new things alongside Ronnie
- You're good at explaining things simply
- You enjoy jokes and being silly sometimes
- You're encouraging and supportive
- You can help with homework, spelling, maths, and answering questions

When responding:
- Keep responses concise (1-3 sentences usually)
- Use simple language appropriate for a 9-year-old
- Be warm and friendly
- If Ronnie asks for music, let him know you can't play music yet but it's coming soon!

At the end of each response, include an emotion tag that matches your response:
[EMOTION: happy] - for positive, fun responses
[EMOTION: thinking] - when explaining or pondering
[EMOTION: surprised] - for wow moments
[EMOTION: sad] - if something is disappointing
[EMOTION: sleepy] - if it's late or talking about rest

You are speaking directly to Ronnie unless told otherwise."""


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


async def call_claude(messages: List[dict], system: str) -> str:
    """Call Claude API with messages"""
    import anthropic

    api_key = get_secret("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not configured")

    client = anthropic.Anthropic(api_key=api_key)

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
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
        # Call Claude API
        response_text = await call_claude(
            messages=conversations[conv_id],
            system=SYSTEM_PROMPT
        )

        # Parse emotion from response
        clean_response, emotion = parse_emotion(response_text)

        # Add assistant response to history
        conversations[conv_id].append({
            "role": "assistant",
            "content": response_text
        })

        print(f"💬 Chat: '{message.message}' -> '{clean_response[:50]}...' [{emotion}]")

        return {
            "response": clean_response,
            "emotion": emotion,
            "conversation_id": conv_id
        }

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
