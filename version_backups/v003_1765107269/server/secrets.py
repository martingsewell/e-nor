"""
E-NOR Secrets Manager
Securely stores API keys and credentials
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Secrets file location - in the project root
SECRETS_FILE = Path(__file__).parent.parent / "secrets.json"

router = APIRouter(prefix="/api/secrets", tags=["secrets"])


class SecretInput(BaseModel):
    """Model for adding/updating a secret"""
    name: str
    value: str


class SecretInfo(BaseModel):
    """Model for secret metadata (no value exposed)"""
    name: str
    configured: bool


# Pre-defined secret templates for the UI
SECRET_TEMPLATES = [
    {
        "name": "ANTHROPIC_API_KEY",
        "label": "Claude API Key",
        "hint": "Ask Dad for this - starts with sk-ant-",
        "required": True
    },
    {
        "name": "GITHUB_TOKEN",
        "label": "GitHub Token",
        "hint": "For E-NOR to update its own code! Ask Dad for this.",
        "required": False
    },
    {
        "name": "AMAZON_EMAIL",
        "label": "Amazon Email",
        "hint": "For playing music (coming soon!)",
        "required": False
    },
    {
        "name": "AMAZON_PASSWORD",
        "label": "Amazon Password",
        "hint": "For playing music (coming soon!)",
        "required": False
    },
    {
        "name": "ELEVENLABS_API_KEY",
        "label": "ElevenLabs API Key",
        "hint": "For voice (coming soon!)",
        "required": False
    }
]


def _load_secrets() -> Dict[str, str]:
    """Load secrets from file"""
    if not SECRETS_FILE.exists():
        return {}
    try:
        with open(SECRETS_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _save_secrets(secrets: Dict[str, str]) -> None:
    """Save secrets to file with restricted permissions"""
    # Write to file
    with open(SECRETS_FILE, "w") as f:
        json.dump(secrets, f, indent=2)

    # Set file permissions to owner read/write only (chmod 600)
    try:
        os.chmod(SECRETS_FILE, 0o600)
    except OSError:
        # May fail on some systems, but file is still saved
        pass


def get_secret(name: str) -> Optional[str]:
    """
    Get a secret value by name.
    For use by other server modules (like chat.py).
    Returns None if secret doesn't exist.
    """
    secrets = _load_secrets()
    return secrets.get(name)


def has_secret(name: str) -> bool:
    """Check if a secret exists"""
    secrets = _load_secrets()
    return bool(name in secrets and secrets[name])


@router.get("")
async def list_secrets() -> Dict:
    """
    List all configured secrets (names only, never values!)
    Also returns templates for the UI to show what can be configured.
    """
    secrets = _load_secrets()

    # Build list of configured secrets
    configured = [
        {"name": name, "configured": True}
        for name in secrets.keys()
        if secrets[name]  # Only show if value is not empty
    ]

    # Build template status
    templates_status = []
    for template in SECRET_TEMPLATES:
        templates_status.append({
            **template,
            "configured": template["name"] in secrets and bool(secrets[template["name"]])
        })

    return {
        "configured": configured,
        "templates": templates_status
    }


@router.post("")
async def set_secret(secret: SecretInput) -> Dict:
    """Add or update a secret"""
    if not secret.name or not secret.name.strip():
        raise HTTPException(status_code=400, detail="Secret name is required")

    if not secret.value:
        raise HTTPException(status_code=400, detail="Secret value is required")

    # Sanitize name (uppercase, alphanumeric and underscores only)
    name = secret.name.strip().upper()
    name = ''.join(c if c.isalnum() or c == '_' else '_' for c in name)

    secrets = _load_secrets()
    secrets[name] = secret.value
    _save_secrets(secrets)

    print(f"🔐 Secret saved: {name}")
    return {"success": True, "name": name, "message": f"Secret '{name}' saved!"}


@router.delete("/{name}")
async def delete_secret(name: str) -> Dict:
    """Delete a secret"""
    secrets = _load_secrets()

    if name not in secrets:
        raise HTTPException(status_code=404, detail=f"Secret '{name}' not found")

    del secrets[name]
    _save_secrets(secrets)

    print(f"🗑️ Secret deleted: {name}")
    return {"success": True, "message": f"Secret '{name}' deleted!"}


@router.get("/check/{name}")
async def check_secret(name: str) -> Dict:
    """Check if a specific secret is configured (without revealing value)"""
    return {
        "name": name,
        "configured": has_secret(name)
    }
