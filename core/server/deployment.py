"""
E-NOR Deployment Status Module
Tracks git deployment status between Pi and remote repository
"""

import subprocess
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional
from fastapi import APIRouter

router = APIRouter(prefix="/api/deployment", tags=["deployment"])

PROJECT_ROOT = Path(__file__).parent.parent.parent
DEPLOY_STATUS_FILE = PROJECT_ROOT / "config" / "deploy_status.json"


def run_git_command(args: list, timeout: int = 30) -> tuple[bool, str]:
    """Run a git command and return (success, output)"""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


def get_local_commit() -> Dict:
    """Get information about the current local commit"""
    success, commit_hash = run_git_command(["rev-parse", "HEAD"])
    if not success:
        return {"error": commit_hash}

    # Get short hash
    _, short_hash = run_git_command(["rev-parse", "--short", "HEAD"])

    # Get commit message
    _, message = run_git_command(["log", "-1", "--pretty=%s"])

    # Get commit date
    _, date_str = run_git_command(["log", "-1", "--pretty=%ci"])

    # Get author
    _, author = run_git_command(["log", "-1", "--pretty=%an"])

    return {
        "hash": commit_hash,
        "short_hash": short_hash,
        "message": message,
        "date": date_str,
        "author": author
    }


def get_remote_commit(branch: str = "main") -> Dict:
    """Fetch and get information about the remote branch"""
    # First fetch the remote
    success, error = run_git_command(["fetch", "origin", branch], timeout=60)
    if not success:
        return {"error": f"Failed to fetch: {error}"}

    # Get remote commit hash
    success, commit_hash = run_git_command(["rev-parse", f"origin/{branch}"])
    if not success:
        return {"error": commit_hash}

    # Get short hash
    _, short_hash = run_git_command(["rev-parse", "--short", f"origin/{branch}"])

    # Get commit message
    _, message = run_git_command(["log", "-1", "--pretty=%s", f"origin/{branch}"])

    # Get commit date
    _, date_str = run_git_command(["log", "-1", "--pretty=%ci", f"origin/{branch}"])

    # Get author
    _, author = run_git_command(["log", "-1", "--pretty=%an", f"origin/{branch}"])

    return {
        "hash": commit_hash,
        "short_hash": short_hash,
        "message": message,
        "date": date_str,
        "author": author
    }


def get_commits_behind() -> int:
    """Get number of commits local is behind remote"""
    success, output = run_git_command(["rev-list", "--count", "HEAD..origin/main"])
    if success and output.isdigit():
        return int(output)
    return -1


def get_commits_ahead() -> int:
    """Get number of commits local is ahead of remote"""
    success, output = run_git_command(["rev-list", "--count", "origin/main..HEAD"])
    if success and output.isdigit():
        return int(output)
    return -1


def check_for_conflicts() -> Dict:
    """Check if there are any merge conflicts or uncommitted changes"""
    # Check for uncommitted changes
    success, status = run_git_command(["status", "--porcelain"])
    has_changes = bool(status.strip()) if success else False

    # Check for merge conflicts
    success, merge_head = run_git_command(["rev-parse", "MERGE_HEAD"])
    in_merge = success  # If MERGE_HEAD exists, we're in a merge

    # Get list of conflicted files if any
    conflicted_files = []
    if success:
        _, unmerged = run_git_command(["diff", "--name-only", "--diff-filter=U"])
        if unmerged:
            conflicted_files = unmerged.strip().split('\n')

    return {
        "has_uncommitted_changes": has_changes,
        "in_merge_conflict": in_merge,
        "conflicted_files": conflicted_files,
        "status_output": status if has_changes else None
    }


def get_last_pull_time() -> Optional[str]:
    """Get the time of the last git pull (from FETCH_HEAD modification time)"""
    fetch_head = PROJECT_ROOT / ".git" / "FETCH_HEAD"
    if fetch_head.exists():
        mtime = fetch_head.stat().st_mtime
        return datetime.fromtimestamp(mtime).isoformat()
    return None


def save_deploy_status(status: Dict):
    """Save deployment status to file"""
    try:
        DEPLOY_STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
        status["last_checked"] = datetime.now().isoformat()
        with open(DEPLOY_STATUS_FILE, 'w') as f:
            json.dump(status, f, indent=2)
    except Exception as e:
        print(f"Failed to save deploy status: {e}")


def format_time_ago(timestamp_str: str) -> str:
    """Format timestamp into friendly 'time ago' format"""
    try:
        if 'T' in timestamp_str:
            created = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        else:
            # Parse git date format: "2025-01-15 10:30:00 +0000"
            created = datetime.strptime(timestamp_str[:19], "%Y-%m-%d %H:%M:%S")

        now = datetime.now()
        diff = now - created

        if diff.days > 1:
            return f"{diff.days} days ago"
        elif diff.days == 1:
            return "yesterday"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            return "just now"
    except:
        return "unknown"


def is_stale_deployment(minutes: int = 10) -> bool:
    """Check if the last pull was more than X minutes ago and we're behind"""
    last_pull = get_last_pull_time()
    if not last_pull:
        return True

    try:
        pull_time = datetime.fromisoformat(last_pull)
        stale_threshold = datetime.now() - timedelta(minutes=minutes)
        return pull_time < stale_threshold
    except:
        return True


# API Endpoints

@router.get("/status")
async def get_deployment_status():
    """Get comprehensive deployment status"""
    local = get_local_commit()
    remote = get_remote_commit()
    conflicts = check_for_conflicts()

    behind = get_commits_behind()
    ahead = get_commits_ahead()
    last_pull = get_last_pull_time()

    # Determine sync status
    if "error" in local or "error" in remote:
        sync_status = "error"
    elif conflicts["in_merge_conflict"]:
        sync_status = "conflict"
    elif behind == 0 and ahead == 0:
        sync_status = "synced"
    elif behind > 0:
        sync_status = "behind"
    elif ahead > 0:
        sync_status = "ahead"
    else:
        sync_status = "unknown"

    # Check if stale
    is_stale = is_stale_deployment(10) and behind > 0

    status = {
        "local": local,
        "remote": remote,
        "sync_status": sync_status,
        "commits_behind": behind,
        "commits_ahead": ahead,
        "last_pull": last_pull,
        "last_pull_ago": format_time_ago(last_pull) if last_pull else "never",
        "conflicts": conflicts,
        "is_stale": is_stale,
        "stale_warning": f"Deployment is {behind} commit(s) behind and hasn't pulled in over 10 minutes" if is_stale else None
    }

    save_deploy_status(status)
    return status


@router.post("/pull")
async def force_pull():
    """Force pull from remote (with stash if needed)"""
    conflicts = check_for_conflicts()

    # If there are uncommitted changes, stash them first
    if conflicts["has_uncommitted_changes"] and not conflicts["in_merge_conflict"]:
        run_git_command(["stash", "push", "-m", "Auto-stash before pull"])

    # Pull
    success, output = run_git_command(["pull", "origin", "main"], timeout=120)

    if success:
        return {
            "success": True,
            "message": "Successfully pulled latest changes",
            "output": output
        }
    else:
        return {
            "success": False,
            "message": "Pull failed",
            "error": output
        }


@router.post("/reset-conflicts")
async def reset_conflicts():
    """Abort merge and reset to clean state"""
    # First try to abort any in-progress merge
    run_git_command(["merge", "--abort"])

    # Reset any staged changes
    run_git_command(["reset", "HEAD"])

    # Discard unstaged changes (be careful!)
    success, output = run_git_command(["checkout", "--", "."])

    if success:
        return {
            "success": True,
            "message": "Conflicts resolved - reset to clean state"
        }
    else:
        return {
            "success": False,
            "message": "Failed to reset",
            "error": output
        }


@router.post("/force-reset")
async def force_reset_to_remote():
    """Force reset local to match remote main (DESTRUCTIVE)"""
    # Fetch latest
    run_git_command(["fetch", "origin", "main"])

    # Hard reset to origin/main
    success, output = run_git_command(["reset", "--hard", "origin/main"])

    if success:
        return {
            "success": True,
            "message": "Force reset to remote main complete",
            "output": output
        }
    else:
        return {
            "success": False,
            "message": "Force reset failed",
            "error": output
        }


@router.post("/push-logs")
async def push_logs():
    """Push debug logs to GitHub logs branch via API"""
    import base64
    import httpx
    from datetime import datetime
    from .secrets import get_secret, has_secret
    from .config import get_config_value

    # Check for GitHub token
    if not has_secret("GITHUB_TOKEN"):
        return {"success": False, "error": "GitHub token not configured"}

    github_token = get_secret("GITHUB_TOKEN")
    owner = get_config_value("github.owner", "")
    repo = get_config_value("github.repo", "")

    if not owner or not repo:
        return {"success": False, "error": "GitHub owner/repo not configured"}

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_filename = f"enor_{timestamp}.log"

    # Collect logs
    log_content = f"=== E-NOR Service Logs ===\nCollected at: {datetime.now().isoformat()}\n\n"

    # Get journalctl logs (if running via systemd)
    try:
        result = subprocess.run(
            ["journalctl", "-u", "enor", "--no-pager", "-n", "1000"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            log_content += result.stdout
        else:
            log_content += "No journalctl logs available (may be running via nohup)\n"
    except Exception as e:
        log_content += f"Failed to get journalctl logs: {e}\n"

    # Get file-based logs (from nohup or file logging)
    log_content += "\n=== File-based Logs (enor.log) ===\n"
    enor_log = PROJECT_ROOT / "logs" / "enor.log"
    if enor_log.exists():
        try:
            result = subprocess.run(
                ["tail", "-n", "500", str(enor_log)],
                capture_output=True,
                text=True,
                timeout=10
            )
            log_content += result.stdout if result.returncode == 0 else "Failed to read enor.log\n"
        except Exception as e:
            log_content += f"Failed to read enor.log: {e}\n"
    else:
        log_content += "enor.log not found\n"

    # Add system info
    log_content += "\n=== System Info ===\n"
    try:
        import socket
        log_content += f"Hostname: {socket.gethostname()}\n"
        uptime_result = subprocess.run(["uptime"], capture_output=True, text=True, timeout=5)
        log_content += f"Uptime: {uptime_result.stdout.strip()}\n"
        free_result = subprocess.run(["free", "-h"], capture_output=True, text=True, timeout=5)
        log_content += f"Memory:\n{free_result.stdout}\n"
    except Exception as e:
        log_content += f"Failed to get system info: {e}\n"

    # Push to GitHub via API
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    api_base = f"https://api.github.com/repos/{owner}/{repo}"

    async with httpx.AsyncClient() as client:
        # Check if logs branch exists
        branch_resp = await client.get(f"{api_base}/branches/logs", headers=headers)

        if branch_resp.status_code == 404:
            # Create logs branch from main
            main_resp = await client.get(f"{api_base}/git/ref/heads/main", headers=headers)
            if main_resp.status_code != 200:
                return {"success": False, "error": "Failed to get main branch"}

            main_sha = main_resp.json()["object"]["sha"]
            create_resp = await client.post(
                f"{api_base}/git/refs",
                headers=headers,
                json={"ref": "refs/heads/logs", "sha": main_sha}
            )
            if create_resp.status_code not in [200, 201]:
                return {"success": False, "error": f"Failed to create logs branch: {create_resp.text}"}

        # Create/update file via Contents API
        file_path = f"logs/{log_filename}"
        content_b64 = base64.b64encode(log_content.encode()).decode()

        put_resp = await client.put(
            f"{api_base}/contents/{file_path}",
            headers=headers,
            json={
                "message": f"Log snapshot: {timestamp}",
                "content": content_b64,
                "branch": "logs"
            }
        )

        if put_resp.status_code in [200, 201]:
            return {
                "success": True,
                "message": "Logs pushed to GitHub",
                "log_file": log_filename,
                "branch": "logs",
                "url": f"https://github.com/{owner}/{repo}/blob/logs/logs/{log_filename}"
            }
        else:
            return {"success": False, "error": f"Failed to push: {put_resp.text}"}


@router.get("/log")
async def get_recent_commits(count: int = 10):
    """Get recent commit log"""
    success, output = run_git_command([
        "log", f"-{count}",
        "--pretty=format:%h|%s|%an|%ci",
        "--date=short"
    ])

    if not success:
        return {"error": output}

    commits = []
    for line in output.strip().split('\n'):
        if line:
            parts = line.split('|')
            if len(parts) >= 4:
                commits.append({
                    "hash": parts[0],
                    "message": parts[1],
                    "author": parts[2],
                    "date": parts[3],
                    "date_ago": format_time_ago(parts[3])
                })

    return {"commits": commits}
