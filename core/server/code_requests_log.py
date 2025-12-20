"""
E-NOR Code Requests Log Module
Tracks recent code requests to prevent duplicates and provide context
"""

import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from pathlib import Path
from fastapi import APIRouter

router = APIRouter(prefix="/api/requests", tags=["requests"])

# Log file location (in config directory)
REQUESTS_LOG_FILE = Path(__file__).parent.parent.parent / "config" / "code_requests.json"


def get_github_repo_url() -> str:
    """Get the GitHub repo URL from config"""
    try:
        from .config import load_config
        config = load_config()
        github = config.get("github", {})
        owner = github.get("owner", "martingsewell")
        repo = github.get("repo", "e-nor")
        return f"https://api.github.com/repos/{owner}/{repo}"
    except ImportError:
        return "https://api.github.com/repos/martingsewell/e-nor"

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


def check_github_issue_status(issue_number: int) -> Optional[str]:
    """Check if a GitHub issue is closed. Returns 'completed' if closed, None if open or on error."""
    try:
        from .secrets import get_secret
        token = get_secret("GITHUB_TOKEN")
        if not token:
            return None  # Can't check without token

        base_url = get_github_repo_url()
        url = f"{base_url}/issues/{issue_number}"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "E-NOR-Robot"
        }
        
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            return 'completed' if data.get('state') == 'closed' else None
    except (urllib.error.HTTPError, Exception):
        # If we can't check (network issue, API error, etc.), don't update
        return None


def sync_github_status(requests: List[dict]) -> bool:
    """Check GitHub status for pending requests and update if needed. Returns True if any changes made."""
    changed = False
    for req in requests:
        # Only check pending/in-progress requests that have issue numbers
        if req.get("status") in ["pending", "in_progress"] and req.get("issue_number"):
            github_status = check_github_issue_status(req["issue_number"])
            if github_status == 'completed' and req.get("status") != "completed":
                req["status"] = "completed"
                req["updated_at"] = datetime.now().isoformat()
                changed = True
                print(f"Auto-updated status for issue #{req['issue_number']} to completed")
    return changed


def get_all_requests() -> List[dict]:
    """Get all requests (for UI display), auto-syncing with GitHub status"""
    requests = load_requests()
    requests = cleanup_old_requests(requests)
    
    # Auto-sync with GitHub status
    if sync_github_status(requests):
        save_requests(requests)  # Save if any changes were made
    
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


@router.get("/{issue_number}/comments")
async def api_get_issue_comments(issue_number: int) -> Dict:
    """Get all comments for a GitHub issue"""
    from .secrets import get_secret
    
    token = get_secret("GITHUB_TOKEN")
    if not token:
        return {"success": False, "message": "GitHub token not configured"}

    try:
        base_url = get_github_repo_url()
        url = f"{base_url}/issues/{issue_number}/comments"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "E-NOR-Robot"
        }

        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            comments_data = json.loads(response.read().decode('utf-8'))

            # Also get the issue data for context
            issue_url = f"{base_url}/issues/{issue_number}"
            issue_req = urllib.request.Request(issue_url, headers=headers)
            with urllib.request.urlopen(issue_req) as issue_response:
                issue_data = json.loads(issue_response.read().decode('utf-8'))
            
            # Format comments for display
            formatted_comments = []
            for comment in comments_data:
                formatted_comments.append({
                    "author": comment["user"]["login"],
                    "avatar_url": comment["user"]["avatar_url"],
                    "body": comment["body"],
                    "created_at": comment["created_at"],
                    "updated_at": comment["updated_at"],
                    "html_url": comment["html_url"]
                })
            
            return {
                "success": True,
                "issue": {
                    "number": issue_data["number"],
                    "title": issue_data["title"],
                    "state": issue_data["state"],
                    "created_at": issue_data["created_at"],
                    "html_url": issue_data["html_url"],
                    "body": issue_data["body"]
                },
                "comments": formatted_comments,
                "comment_count": len(formatted_comments)
            }
            
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        return {"success": False, "message": f"GitHub API error: {e.code} - {error_body}"}
    except Exception as e:
        return {"success": False, "message": f"Error fetching comments: {str(e)}"}
