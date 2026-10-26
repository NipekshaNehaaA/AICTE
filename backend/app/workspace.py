"""
Workspace Isolation Module for AICTE Platform.
Manages two isolated environments:
1. "live": Strict production environment (real accounts, real TOTP MFA, 0 demo accounts/institutions).
2. "sandbox": Demonstration workspace (synthetic institutions, 1-click personas, time-travel, demo PIN 123456).

Workspaces are completely isolated:
- Separate SQLite databases: aicte_live.db and aicte_sandbox.db.
- Separate storage directories: storage_data/live and storage_data/sandbox.
- Separate audit ledgers.
- Tokens carry a "ws" claim ("live" or "sandbox").
"""

from contextvars import ContextVar
from typing import Optional, Dict
from fastapi import Request, HTTPException, status
import jwt

# Context variable tracking active workspace for current request thread/task
current_workspace_var: ContextVar[str] = ContextVar("current_workspace", default="live")

# Global in-memory evaluator delivery override for Sandbox workspace
_sandbox_overrides: Dict[str, Optional[str]] = {
    "override_email": None,
    "override_whatsapp": None,
}

def set_sandbox_override(email: Optional[str] = None, whatsapp: Optional[str] = None):
    """Sets override recipient for Sandbox messages. Evaluator receives messages instead of fake institutions."""
    _sandbox_overrides["override_email"] = email.strip() if (email and email.strip()) else None
    _sandbox_overrides["override_whatsapp"] = whatsapp.strip() if (whatsapp and whatsapp.strip()) else None

def get_sandbox_override() -> Dict[str, Optional[str]]:
    """Returns the current sandbox override recipient."""
    return dict(_sandbox_overrides)

def clear_sandbox_override():
    """Clears any active sandbox override recipient."""
    _sandbox_overrides["override_email"] = None
    _sandbox_overrides["override_whatsapp"] = None

def extract_workspace_from_token(token: str) -> Optional[str]:
    """Inspects JWT token payload to extract 'ws' claim without verifying signature twice."""
    try:
        from app.config import settings
        # We decode with algorithm and secret to verify token integrity
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_exp": False},
        )
        ws = payload.get("ws")
        if ws in ("live", "sandbox"):
            return ws
    except Exception:
        pass
    return None

def resolve_workspace(request: Optional[Request] = None) -> str:
    """
    Resolves the target workspace for an incoming request:
    1. If a valid Bearer token is provided, uses its 'ws' claim.
    2. If an X-Workspace header is provided with a token, validates that they match (prevents token cross-usage).
    3. If unauthenticated, uses the X-Workspace header (defaulting to 'live').
    """
    if request is None:
        return current_workspace_var.get()

    header_ws: Optional[str] = None
    if hasattr(request, "headers"):
        raw_header = request.headers.get("x-workspace")
        if raw_header:
            clean = raw_header.strip().lower()
            if clean in ("live", "sandbox"):
                header_ws = clean

    token_ws: Optional[str] = None
    if hasattr(request, "headers"):
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()
            token_ws = extract_workspace_from_token(token)

    # Cross-workspace token enforcement
    if token_ws:
        if header_ws and header_ws != token_ws:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Workspace Violation: Provided token is bound to '{token_ws}' workspace and cannot access '{header_ws}' workspace.",
            )
        current_workspace_var.set(token_ws)
        return token_ws

    # Fallback for unauthenticated requests (login, signup, public track)
    ws = header_ws or "live"
    current_workspace_var.set(ws)
    return ws

def require_workspace(expected_ws: str, request: Request):
    """Guards endpoints that exist strictly in one workspace (e.g. personas only in sandbox)."""
    ws = resolve_workspace(request)
    if ws != expected_ws.lower():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Not Found: Endpoint is not available in '{ws}' workspace.",
        )
