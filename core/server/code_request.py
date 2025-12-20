"""
E-NOR Code Request Module
Allows E-NOR to request code changes by creating GitHub issues
"""

import json
import urllib.request
import urllib.error
import base64
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .secrets import get_secret, has_secret

router = APIRouter(prefix="/api/code", tags=["code"])

def get_github_config():
    """Get GitHub owner and repo from config"""
    try:
        from .config import load_config
        config = load_config()
        github = config.get("github", {})
        return github.get("owner", "martingsewell"), github.get("repo", "e-nor")
    except ImportError:
        return "martingsewell", "e-nor"


def get_child_name():
    """Get child's name from config"""
    try:
        from .config import get_child_name as get_name
        return get_name() or "the child"
    except ImportError:
        return "the child"


class CodeRequest(BaseModel):
    """Model for code change request"""
    title: str
    description: str
    requested_by: str = "Ronnie"


class CodeRequestResponse(BaseModel):
    """Response after creating a code request"""
    success: bool
    message: str
    issue_url: Optional[str] = None
    issue_number: Optional[int] = None


def upload_github_asset(file_path: str, filename: str) -> str:
    """
    Upload a file to GitHub as a release asset or use GitHub's asset upload API.
    For simplicity, we'll embed the image as a data URL in the issue body.
    Returns the markdown image reference.
    """
    try:
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        # Convert to base64 for embedding
        b64_data = base64.b64encode(file_data).decode('utf-8')
        data_url = f"data:image/png;base64,{b64_data}"
        
        # Create a markdown image with the data URL
        # Note: GitHub issues don't support data URLs, but we can provide file info
        file_size_kb = len(file_data) // 1024
        return f"**Screenshot captured** (Size: {file_size_kb} KB)\n\n*Screenshot was captured but cannot be directly embedded in GitHub issues. The image was {file_size_kb} KB in size.*"
        
    except Exception as e:
        print(f"Failed to process screenshot file: {e}")
        return "**Screenshot capture failed**"


def create_github_issue(title: str, body: str, labels: list = None, screenshot_path: Optional[str] = None) -> dict:
    """
    Create a GitHub issue using the REST API.
    Returns the created issue data or raises an exception.
    """
    token = get_secret("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN not configured")

    # Add screenshot info to body if provided
    if screenshot_path:
        screenshot_info = upload_github_asset(screenshot_path, "screenshot.png")
        body += f"\n\n### Screenshot\n{screenshot_info}"

    owner, repo = get_github_config()
    url = f"https://api.github.com/repos/{owner}/{repo}/issues"

    data = {
        "title": title,
        "body": body,
        "labels": labels or ["enor-request", "automated"]
    }

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "User-Agent": "E-NOR-Robot"
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8'),
        headers=headers,
        method='POST'
    )

    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        raise Exception(f"GitHub API error: {e.code} - {error_body}")


@router.post("")
async def request_code_change(request: CodeRequest) -> CodeRequestResponse:
    """
    Create a GitHub issue for a code change request.
    This will trigger Claude Code to implement the change.
    """
    # Check if GitHub token is configured
    if not has_secret("GITHUB_TOKEN"):
        return CodeRequestResponse(
            success=False,
            message="I can't update my code yet - Dad needs to add the GitHub token in settings!"
        )

    # Build the issue body with context
    body = f"""## Code Change Request from {request.requested_by}

**Request:** {request.description}

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

    try:
        issue = create_github_issue(
            title=f"[E-NOR Request] {request.title}",
            body=body,
            labels=["enor-request", "automated"]
        )

        print(f"Created issue #{issue['number']}: {issue['title']}")

        return CodeRequestResponse(
            success=True,
            message=f"I've created a request to update my code! Issue #{issue['number']} - Dad or Claude Code will implement it soon.",
            issue_url=issue["html_url"],
            issue_number=issue["number"]
        )

    except ValueError as e:
        return CodeRequestResponse(
            success=False,
            message="I can't update my code yet - the GitHub token isn't set up!"
        )
    except Exception as e:
        print(f"Error creating issue: {e}")
        return CodeRequestResponse(
            success=False,
            message=f"Something went wrong creating the request: {str(e)}"
        )


@router.get("/status")
async def code_request_status() -> dict:
    """Check if code requests are enabled (GitHub token configured)"""
    has_token = has_secret("GITHUB_TOKEN")
    return {
        "enabled": has_token,
        "message": "Code requests enabled!" if has_token else "GitHub token not configured"
    }
