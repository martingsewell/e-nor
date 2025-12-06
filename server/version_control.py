"""
E-NOR Version Control System
Simple version tracking for code changes made to E-NOR
"""

import json
import os
import shutil
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/versions", tags=["versions"])

# Version storage location
VERSIONS_FILE = Path(__file__).parent.parent / "versions.json"
BACKUP_DIR = Path(__file__).parent.parent / "version_backups"

# Files to track for versions
TRACKED_FILES = [
    "web/index.html",
    "server/main.py", 
    "server/chat.py",
    "server/secrets.py",
    "server/memories.py",
    "server/code_request.py"
]

def ensure_backup_dir():
    """Ensure backup directory exists"""
    BACKUP_DIR.mkdir(exist_ok=True)

def load_versions() -> List[Dict]:
    """Load version history from file"""
    if not VERSIONS_FILE.exists():
        return []
    
    try:
        with open(VERSIONS_FILE, 'r') as f:
            data = json.load(f)
            return data.get("versions", [])
    except (json.JSONDecodeError, IOError):
        return []

def save_versions(versions: List[Dict]) -> bool:
    """Save version history to file"""
    try:
        with open(VERSIONS_FILE, 'w') as f:
            json.dump({"versions": versions}, f, indent=2)
        return True
    except IOError:
        return False

def get_file_hash(file_path: Path) -> str:
    """Get a simple hash of file content for change detection"""
    try:
        import hashlib
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()[:8]
    except:
        return "unknown"

def create_backup(version_id: str, description: str) -> bool:
    """Create a backup of all tracked files"""
    ensure_backup_dir()
    backup_path = BACKUP_DIR / version_id
    backup_path.mkdir(exist_ok=True)
    
    base_dir = Path(__file__).parent.parent
    
    try:
        for file_path in TRACKED_FILES:
            source = base_dir / file_path
            if source.exists():
                dest = backup_path / file_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, dest)
        
        # Save metadata
        metadata = {
            "description": description,
            "created_at": datetime.now().isoformat(),
            "files": TRACKED_FILES
        }
        with open(backup_path / "metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
            
        return True
    except Exception as e:
        print(f"Error creating backup: {e}")
        return False

def restore_backup(version_id: str) -> bool:
    """Restore files from a backup"""
    backup_path = BACKUP_DIR / version_id
    if not backup_path.exists():
        return False
    
    base_dir = Path(__file__).parent.parent
    
    try:
        for file_path in TRACKED_FILES:
            backup_file = backup_path / file_path
            if backup_file.exists():
                dest = base_dir / file_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup_file, dest)
        return True
    except Exception as e:
        print(f"Error restoring backup: {e}")
        return False

def add_version(description: str, status: str = "working") -> Dict:
    """Add a new version entry"""
    versions = load_versions()
    
    # Generate version ID
    version_id = f"v{len(versions) + 1:03d}_{int(datetime.now().timestamp())}"
    
    # Create backup
    backup_success = create_backup(version_id, description)
    
    new_version = {
        "id": version_id,
        "version_number": len(versions) + 1,
        "description": description,
        "status": status,  # working, broken, testing
        "created_at": datetime.now().isoformat(),
        "is_current": True,
        "backup_available": backup_success,
        "change_summary": get_change_summary()
    }
    
    # Mark all other versions as not current
    for version in versions:
        version["is_current"] = False
    
    versions.append(new_version)
    
    # Keep only last 10 versions
    if len(versions) > 10:
        # Remove old backups
        old_version = versions.pop(0)
        old_backup = BACKUP_DIR / old_version["id"]
        if old_backup.exists():
            shutil.rmtree(old_backup, ignore_errors=True)
    
    save_versions(versions)
    return new_version

def get_change_summary() -> List[str]:
    """Get a summary of what files have changed recently"""
    summary = []
    base_dir = Path(__file__).parent.parent
    
    for file_path in TRACKED_FILES:
        file_full_path = base_dir / file_path
        if file_full_path.exists():
            stat = file_full_path.stat()
            # Check if modified in last hour (indicating recent change)
            if (datetime.now().timestamp() - stat.st_mtime) < 3600:
                summary.append(file_path)
    
    return summary

def format_time_ago(timestamp_str: str) -> str:
    """Format timestamp into friendly 'time ago' format"""
    try:
        created = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
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

def update_version_status(version_id: str, status: str) -> bool:
    """Update the status of a version"""
    versions = load_versions()
    
    for version in versions:
        if version["id"] == version_id:
            version["status"] = status
            save_versions(versions)
            return True
    
    return False

# API Endpoints

@router.get("")
async def get_versions():
    """Get all versions for display"""
    versions = load_versions()
    
    # Format for display
    for version in versions:
        version["time_ago"] = format_time_ago(version["created_at"])
        version["status_emoji"] = {
            "working": "✅",
            "broken": "❌", 
            "testing": "🔄"
        }.get(version["status"], "❓")
    
    return {
        "versions": versions,
        "current_version": next((v for v in versions if v.get("is_current")), None),
        "total_versions": len(versions)
    }

@router.post("")
async def create_version(description: str, status: str = "working"):
    """Create a new version"""
    if not description.strip():
        raise HTTPException(status_code=400, detail="Description is required")
    
    valid_statuses = ["working", "broken", "testing"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Status must be one of: {valid_statuses}")
    
    new_version = add_version(description, status)
    return {"success": True, "version": new_version}

@router.post("/{version_id}/rollback")
async def rollback_version(version_id: str):
    """Rollback to a specific version"""
    versions = load_versions()
    
    # Find the target version
    target_version = None
    for version in versions:
        if version["id"] == version_id:
            target_version = version
            break
    
    if not target_version:
        raise HTTPException(status_code=404, detail="Version not found")
    
    if not target_version.get("backup_available"):
        raise HTTPException(status_code=400, detail="No backup available for this version")
    
    # Perform rollback
    success = restore_backup(version_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to restore backup")
    
    # Update version status
    for version in versions:
        version["is_current"] = (version["id"] == version_id)
    
    save_versions(versions)
    
    return {
        "success": True,
        "message": f"Successfully rolled back to version {target_version['version_number']}: {target_version['description']}"
    }

@router.put("/{version_id}/status")
async def update_status(version_id: str, status: str):
    """Update version status"""
    valid_statuses = ["working", "broken", "testing"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Status must be one of: {valid_statuses}")
    
    success = update_version_status(version_id, status)
    if not success:
        raise HTTPException(status_code=404, detail="Version not found")
    
    return {"success": True, "message": f"Version status updated to {status}"}

# Auto-create initial version if none exist
def init_version_system():
    """Initialize version system with current state if no versions exist"""
    versions = load_versions()
    if not versions:
        print("🔄 Initializing version control system...")
        add_version("Initial E-NOR setup", "working")
        print("✅ Version control system initialized")

# Call on import
init_version_system()