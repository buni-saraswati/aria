from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from config import Config

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# key → role mapping
def _resolve_role(api_key: str) -> str:
    if api_key == Config.API_KEY_ADMIN:
        return "admin"
    if api_key == Config.API_KEY_APPROVER:
        return "approver"
    if api_key == Config.API_KEY_AGENT:
        return "agent"
    return None


def require_agent(api_key: str = Security(API_KEY_HEADER)):
    """
    Minimum access — agents and above.
    Allows: agent, approver, admin
    """
    role = _resolve_role(api_key)
    if role not in ("agent", "approver", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API key. Required role: agent or above."
        )
    return role


def require_approver(api_key: str = Security(API_KEY_HEADER)):
    """
    Approver access and above.
    Allows: approver, admin
    """
    role = _resolve_role(api_key)
    if role not in ("approver", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API key. Required role: approver or above."
        )
    return role


def require_admin(api_key: str = Security(API_KEY_HEADER)):
    """
    Admin only.
    """
    role = _resolve_role(api_key)
    if role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API key. Required role: admin."
        )
    return role