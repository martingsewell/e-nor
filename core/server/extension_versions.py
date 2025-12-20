"""
E-NOR Extension Version Control
Tracks versions of child-created extensions for rollback and management
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/extension-versions", tags=["extension-versions"])

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
EXTENSIONS_DIR = PROJECT_ROOT / "extensions"
BACKUPS_DIR = EXTENSIONS_DIR / ".backups"
VERSIONS_FILE = EXTENSIONS_DIR / ".versions.json"


def ensure_dirs():
    """Ensure required directories exist"""
    EXTENSIONS_DIR.mkdir(parents=True, exist_ok=True)
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)


def load_versions_db() -> Dict:
    """Load the versions database"""
    if not VERSIONS_FILE.exists():
        return {"extensions": {}}

    try:
        with open(VERSIONS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"extensions": {}}


def save_versions_db(db: Dict) -> bool:
    """Save the versions database"""
    try:
        ensure_dirs()
        with open(VERSIONS_FILE, 'w') as f:
            json.dump(db, f, indent=2)
        return True
    except IOError:
        return False


def get_extension_versions(extension_id: str) -> List[Dict]:
    """Get all versions for an extension"""
    db = load_versions_db()
    return db.get("extensions", {}).get(extension_id, {}).get("versions", [])


def backup_extension(extension_id: str, description: str = "Auto backup") -> Optional[str]:
    """
    Create a backup of an extension before modification.
    Returns the version_id if successful, None otherwise.
    """
    ensure_dirs()

    extension_path = EXTENSIONS_DIR / extension_id
    if not extension_path.exists():
        return None

    # Generate version ID
    timestamp = int(datetime.now().timestamp())
    version_id = f"{extension_id}_v{timestamp}"

    # Create backup directory
    backup_path = BACKUPS_DIR / extension_id / version_id
    backup_path.mkdir(parents=True, exist_ok=True)

    try:
        # Copy all extension files
        for item in extension_path.iterdir():
            if item.is_file():
                shutil.copy2(item, backup_path / item.name)
            elif item.is_dir() and not item.name.startswith('.'):
                shutil.copytree(item, backup_path / item.name)

        # Load manifest for metadata
        manifest_file = extension_path / "manifest.json"
        manifest = {}
        if manifest_file.exists():
            with open(manifest_file, 'r') as f:
                manifest = json.load(f)

        # Update versions database
        db = load_versions_db()
        if "extensions" not in db:
            db["extensions"] = {}
        if extension_id not in db["extensions"]:
            db["extensions"][extension_id] = {
                "name": manifest.get("name", extension_id),
                "versions": []
            }

        version_entry = {
            "version_id": version_id,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "status": "working",  # working, broken, testing
            "manifest_version": manifest.get("version", "unknown"),
            "is_current": False
        }

        # Mark all previous as not current
        for v in db["extensions"][extension_id]["versions"]:
            v["is_current"] = False

        db["extensions"][extension_id]["versions"].append(version_entry)

        # Keep only last 5 versions per extension
        versions = db["extensions"][extension_id]["versions"]
        if len(versions) > 5:
            old_version = versions.pop(0)
            # Remove old backup
            old_backup = BACKUPS_DIR / extension_id / old_version["version_id"]
            if old_backup.exists():
                shutil.rmtree(old_backup, ignore_errors=True)

        save_versions_db(db)
        return version_id

    except Exception as e:
        print(f"Error backing up extension {extension_id}: {e}")
        return None


def restore_extension(extension_id: str, version_id: str) -> bool:
    """Restore an extension to a previous version"""
    backup_path = BACKUPS_DIR / extension_id / version_id
    if not backup_path.exists():
        return False

    extension_path = EXTENSIONS_DIR / extension_id

    try:
        # Backup current state first (so we can undo)
        backup_extension(extension_id, f"Before rollback to {version_id}")

        # Clear current extension (except hidden files)
        if extension_path.exists():
            for item in extension_path.iterdir():
                if not item.name.startswith('.'):
                    if item.is_file():
                        item.unlink()
                    else:
                        shutil.rmtree(item)
        else:
            extension_path.mkdir(parents=True, exist_ok=True)

        # Restore from backup
        for item in backup_path.iterdir():
            if item.is_file():
                shutil.copy2(item, extension_path / item.name)
            elif item.is_dir():
                shutil.copytree(item, extension_path / item.name)

        # Update versions database
        db = load_versions_db()
        if extension_id in db.get("extensions", {}):
            for v in db["extensions"][extension_id]["versions"]:
                v["is_current"] = (v["version_id"] == version_id)
            save_versions_db(db)

        return True

    except Exception as e:
        print(f"Error restoring extension {extension_id}: {e}")
        return False


def set_version_status(extension_id: str, version_id: str, status: str) -> bool:
    """Update the status of a version (working, broken, testing)"""
    db = load_versions_db()

    if extension_id not in db.get("extensions", {}):
        return False

    for v in db["extensions"][extension_id]["versions"]:
        if v["version_id"] == version_id:
            v["status"] = status
            save_versions_db(db)
            return True

    return False


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


# API Endpoints

@router.get("")
async def list_all_extension_versions() -> Dict:
    """Get version info for all extensions"""
    db = load_versions_db()

    result = {}
    for ext_id, ext_data in db.get("extensions", {}).items():
        versions = ext_data.get("versions", [])
        for v in versions:
            v["time_ago"] = format_time_ago(v["created_at"])
            v["status_emoji"] = {
                "working": "✓",
                "broken": "✗",
                "testing": "?"
            }.get(v["status"], "?")

        result[ext_id] = {
            "name": ext_data.get("name", ext_id),
            "versions": versions,
            "version_count": len(versions)
        }

    return {"extensions": result}


@router.get("/{extension_id}")
async def get_extension_version_history(extension_id: str) -> Dict:
    """Get version history for a specific extension"""
    versions = get_extension_versions(extension_id)

    for v in versions:
        v["time_ago"] = format_time_ago(v["created_at"])
        v["status_emoji"] = {
            "working": "✓",
            "broken": "✗",
            "testing": "?"
        }.get(v["status"], "?")

    return {
        "extension_id": extension_id,
        "versions": versions,
        "version_count": len(versions)
    }


@router.post("/{extension_id}/backup")
async def create_extension_backup(extension_id: str, description: str = "Manual backup") -> Dict:
    """Create a backup of an extension"""
    version_id = backup_extension(extension_id, description)

    if version_id:
        return {"success": True, "version_id": version_id, "message": "Backup created"}
    else:
        raise HTTPException(status_code=400, detail="Failed to create backup")


@router.post("/{extension_id}/rollback/{version_id}")
async def rollback_extension(extension_id: str, version_id: str) -> Dict:
    """Rollback an extension to a previous version"""
    success = restore_extension(extension_id, version_id)

    if success:
        return {"success": True, "message": f"Rolled back to {version_id}"}
    else:
        raise HTTPException(status_code=400, detail="Failed to rollback")


@router.put("/{extension_id}/{version_id}/status")
async def update_version_status(extension_id: str, version_id: str, status: str) -> Dict:
    """Update the status of a version"""
    valid_statuses = ["working", "broken", "testing"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Status must be one of: {valid_statuses}")

    success = set_version_status(extension_id, version_id, status)

    if success:
        return {"success": True, "message": f"Status updated to {status}"}
    else:
        raise HTTPException(status_code=404, detail="Version not found")
