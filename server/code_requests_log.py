"""
E-NOR Code Requests Log Module
Tracks recent code requests to prevent duplicates and provide context
"""

import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from pathlib import Path
from fastapi import APIRouter

router = APIRouter(prefix="/api/requests", tags=["requests"])

# Log file location (same directory as memories.json)
REQUESTS_LOG_FILE = Path(__file__).parent.parent / "code_requests.json"

# How long to keep requests in log (7 days)
REQUEST_EXPIRY_DAYS = 7


def load_requests() -> List[dict]:
    """Load all code requests from file"""
    if not REQUESTS_LOG_FILE.exists():
        return []

    try:
        with open(REQUESTS_LOG_FILE, 'r') as f:
            data = json.load(f)
            return data.get("requests", [])
    except (json.JSONDecodeError, IOError):
        return []


def save_requests(requests: List[dict]) -> bool:
    """Save requests to file"""
    try:
        with open(REQUESTS_LOG_FILE, 'w') as f:
            json.dump({"requests": requests}, f, indent=2)
        return True
    except IOError:
        return False


def cleanup_old_requests(requests: List[dict]) -> List[dict]:
    """Remove requests older than REQUEST_EXPIRY_DAYS"""
    cutoff = datetime.now() - timedelta(days=REQUEST_EXPIRY_DAYS)
    cutoff_str = cutoff.isoformat()

    return [r for r in requests if r.get("created_at", "") > cutoff_str]


def normalize_text(text: str) -> str:
    """Normalize text for comparison (lowercase, strip whitespace)"""
    return text.lower().strip()


def is_similar_request(new_title: str, new_desc: str, existing: dict) -> bool:
    """
    Check if a new request is similar to an existing one.
    Returns True if they appear to be the same request.
    """
    new_title_norm = normalize_text(new_title)
    new_desc_norm = normalize_text(new_desc)

    existing_title = normalize_text(existing.get("title", ""))
    existing_desc = normalize_text(existing.get("description", ""))

    # Check for exact or near-exact title match
    if new_title_norm == existing_title:
        return True

    # Check if one title contains the other (handles "add rainbow" vs "add rainbow mode")
    if new_title_norm in existing_title or existing_title in new_title_norm:
        # Also check description overlap for better matching
        if len(new_title_norm) > 5:  # Only for meaningful titles
            return True

    # Check for significant keyword overlap in titles
    new_words = set(new_title_norm.split())
    existing_words = set(existing_title.split())

    # Remove common words
    common_words = {"add", "make", "change", "the", "a", "an", "to", "for", "my", "me"}
    new_words = new_words - common_words
    existing_words = existing_words - common_words

    if new_words and existing_words:
        overlap = new_words & existing_words
        # If more than half the meaningful words match, it's probably similar
        if len(overlap) >= min(len(new_words), len(existing_words)) * 0.5:
            return True

    return False


def find_duplicate(title: str, description: str) -> Optional[dict]:
    """
    Check if a similar request already exists.
    Returns the existing request if found, None otherwise.
    """
    requests = load_requests()
    requests = cleanup_old_requests(requests)

    for req in requests:
        # Only check pending or in-progress requests
        if req.get("status") in ["pending", "in_progress"]:
            if is_similar_request(title, description, req):
                return req

    return None


def add_request(title: str, description: str, issue_number: Optional[int] = None, issue_url: Optional[str] = None) -> dict:
    """
    Add a new request to the log.
    Returns the created request entry.
    """
    requests = load_requests()
    requests = cleanup_old_requests(requests)

    new_request = {
        "title": title,
        "description": description,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "issue_number": issue_number,
        "issue_url": issue_url
    }

    requests.append(new_request)

    # Keep only last 20 requests
    if len(requests) > 20:
        requests = requests[-20:]

    save_requests(requests)
    return new_request


def update_request_status(issue_number: int, status: str) -> bool:
    """Update the status of a request by issue number"""
    requests = load_requests()

    for req in requests:
        if req.get("issue_number") == issue_number:
            req["status"] = status
            req["updated_at"] = datetime.now().isoformat()
            save_requests(requests)
            return True

    return False


def get_pending_requests() -> List[dict]:
    """Get all pending/in-progress requests"""
    requests = load_requests()
    requests = cleanup_old_requests(requests)

    return [r for r in requests if r.get("status") in ["pending", "in_progress"]]


def get_requests_for_prompt() -> str:
    """Get pending requests formatted for the system prompt"""
    pending = get_pending_requests()

    if not pending:
        return ""

    text = "\n\nCode changes already requested (don't request these again):\n"
    for req in pending:
        issue_num = req.get("issue_number")
        issue_str = f" (Issue #{issue_num})" if issue_num else ""
        text += f"- {req['title']}{issue_str}\n"

    return text


def get_all_requests() -> List[dict]:
    """Get all requests (for UI display)"""
    requests = load_requests()
    requests = cleanup_old_requests(requests)
    save_requests(requests)  # Save cleaned up list
    return requests


# API Endpoints

@router.get("")
async def api_get_requests() -> Dict:
    """Get all code requests for display in the UI"""
    all_requests = get_all_requests()
    pending = [r for r in all_requests if r.get("status") in ["pending", "in_progress"]]
    completed = [r for r in all_requests if r.get("status") == "completed"]

    return {
        "requests": all_requests,
        "pending": pending,
        "completed": completed,
        "pending_count": len(pending)
    }


@router.get("/pending")
async def api_get_pending() -> Dict:
    """Get only pending/in-progress requests"""
    pending = get_pending_requests()
    return {
        "pending": pending,
        "count": len(pending)
    }


@router.post("/{issue_number}/status")
async def api_update_status(issue_number: int, status: str) -> Dict:
    """Update the status of a request (called by webhook or manually)"""
    valid_statuses = ["pending", "in_progress", "completed", "failed"]
    if status not in valid_statuses:
        return {"success": False, "message": f"Invalid status. Must be one of: {valid_statuses}"}

    success = update_request_status(issue_number, status)
    return {
        "success": success,
        "message": f"Status updated to {status}" if success else "Request not found"
    }


@router.delete("/{issue_number}")
async def api_delete_request(issue_number: int) -> Dict:
    """Remove a request from the log"""
    requests = load_requests()
    original_len = len(requests)
    requests = [r for r in requests if r.get("issue_number") != issue_number]

    if len(requests) < original_len:
        save_requests(requests)
        return {"success": True, "message": "Request removed"}
    return {"success": False, "message": "Request not found"}
