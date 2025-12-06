"""
E-NOR Memory Module
Stores and retrieves memories about Ronnie
"""

import json
import os
from typing import Dict, List, Optional
from fastapi import APIRouter
from pydantic import BaseModel
from pathlib import Path

router = APIRouter(prefix="/api/memories", tags=["memories"])

# Memory file location (same directory as secrets.json)
MEMORY_FILE = Path(__file__).parent.parent / "memories.json"


def load_memories() -> List[str]:
    """Load all memories from file"""
    if not MEMORY_FILE.exists():
        return []

    try:
        with open(MEMORY_FILE, 'r') as f:
            data = json.load(f)
            return data.get("memories", [])
    except (json.JSONDecodeError, IOError):
        return []


def save_memory(memory: str) -> bool:
    """Add a new memory to the file"""
    memories = load_memories()

    # Avoid duplicate memories
    if memory.lower().strip() in [m.lower().strip() for m in memories]:
        return False

    memories.append(memory.strip())

    # Keep only last 50 memories to avoid bloat
    if len(memories) > 50:
        memories = memories[-50:]

    try:
        with open(MEMORY_FILE, 'w') as f:
            json.dump({"memories": memories}, f, indent=2)
        return True
    except IOError:
        return False


def delete_memory(index: int) -> bool:
    """Delete a memory by index"""
    memories = load_memories()

    if 0 <= index < len(memories):
        memories.pop(index)
        try:
            with open(MEMORY_FILE, 'w') as f:
                json.dump({"memories": memories}, f, indent=2)
            return True
        except IOError:
            return False
    return False


def clear_all_memories() -> bool:
    """Clear all memories"""
    try:
        with open(MEMORY_FILE, 'w') as f:
            json.dump({"memories": []}, f, indent=2)
        return True
    except IOError:
        return False


def get_memories_for_prompt() -> str:
    """Get memories formatted for the system prompt"""
    memories = load_memories()
    if not memories:
        return ""

    memory_text = "\n\nThings you remember about Ronnie:\n"
    for memory in memories:
        memory_text += f"- {memory}\n"

    return memory_text


# API Endpoints

class MemoryInput(BaseModel):
    memory: str


@router.get("")
async def get_all_memories() -> Dict:
    """Get all stored memories"""
    return {"memories": load_memories()}


@router.post("")
async def add_memory(data: MemoryInput) -> Dict:
    """Add a new memory"""
    if not data.memory or len(data.memory) < 3:
        return {"success": False, "message": "Memory too short"}

    success = save_memory(data.memory)
    if success:
        print(f"🧠 New memory saved: {data.memory}")
        return {"success": True, "message": "Memory saved!"}
    else:
        return {"success": False, "message": "Memory already exists or save failed"}


@router.delete("/{index}")
async def remove_memory(index: int) -> Dict:
    """Delete a memory by index"""
    success = delete_memory(index)
    return {"success": success}


@router.delete("")
async def clear_memories() -> Dict:
    """Clear all memories"""
    success = clear_all_memories()
    return {"success": success}
