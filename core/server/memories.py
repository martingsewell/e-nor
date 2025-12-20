"""
E-NOR Memory Module
Stores and retrieves memories about the child
"""

import json
import os
from typing import Dict, List, Optional
from fastapi import APIRouter
from pydantic import BaseModel
from pathlib import Path

router = APIRouter(prefix="/api/memories", tags=["memories"])

# Memory file location (in config directory)
MEMORY_FILE = Path(__file__).parent.parent.parent / "config" / "memories.json"


def get_max_memories() -> int:
    """Get max memories from config"""
    try:
        from .config import get_config_value
        return get_config_value("limits.max_memories", 50)
    except ImportError:
        return 50


def get_child_name_for_prompt() -> str:
    """Get child's name from config for use in prompts"""
    try:
        from .config import get_child_name
        name = get_child_name()
        return name if name else "the child"
    except ImportError:
        return "the child"


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

    # Keep only last N memories from config
    max_memories = get_max_memories()
    if len(memories) > max_memories:
        memories = memories[-max_memories:]

    try:
        MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
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


def update_memory(topic: str, new_fact: str) -> tuple[bool, Optional[str]]:
    """
    Update a memory about a topic.
    Finds memories containing the topic keywords and replaces with new fact.
    Returns (success, old_memory_that_was_replaced or None)
    """
    memories = load_memories()
    topic_lower = topic.lower()

    # Find memories that match the topic
    for i, memory in enumerate(memories):
        if topic_lower in memory.lower():
            old_memory = memories[i]
            memories[i] = new_fact.strip()
            try:
                with open(MEMORY_FILE, 'w') as f:
                    json.dump({"memories": memories}, f, indent=2)
                return True, old_memory
            except IOError:
                return False, None

    # No existing memory found - just add the new one
    return save_memory(new_fact), None


def forget_memory(topic: str) -> tuple[bool, Optional[str]]:
    """
    Delete a memory about a topic.
    Finds memories containing the topic keywords and removes them.
    Returns (success, deleted_memory or None)
    """
    memories = load_memories()
    topic_lower = topic.lower()

    # Find memories that match the topic
    for i, memory in enumerate(memories):
        if topic_lower in memory.lower():
            deleted_memory = memories.pop(i)
            try:
                with open(MEMORY_FILE, 'w') as f:
                    json.dump({"memories": memories}, f, indent=2)
                return True, deleted_memory
            except IOError:
                return False, None

    return False, None


def clear_all_memories() -> bool:
    """Clear all memories"""
    try:
        MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
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

    child_name = get_child_name_for_prompt()
    memory_text = f"\n\nThings you remember about {child_name}:\n"
    for memory in memories:
        memory_text += f"- {memory}\n"

    return memory_text


def get_memory_count() -> int:
    """Get the current number of memories"""
    return len(load_memories())


def get_memory_stats() -> Dict:
    """Get memory statistics"""
    memories = load_memories()
    max_mem = get_max_memories()
    return {
        "count": len(memories),
        "max": max_mem,
        "available": max_mem - len(memories)
    }


# API Endpoints

class MemoryInput(BaseModel):
    memory: str


@router.get("")
async def get_all_memories() -> Dict:
    """Get all stored memories"""
    stats = get_memory_stats()
    return {
        "memories": load_memories(),
        "count": stats["count"],
        "max": stats["max"]
    }


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


@router.get("/stats")
async def memory_stats() -> Dict:
    """Get memory statistics"""
    return get_memory_stats()
