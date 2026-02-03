"""
COROS Platform login functionality.

Provides the LoginResult interface matching the garmin_mcp pattern.
"""

from dataclasses import dataclass
from typing import Optional

from coros_mcp.coros_client import CorosClient


@dataclass
class LoginResult:
    """Result of a login attempt."""
    success: bool
    tokens: Optional[str] = None
    display_name: Optional[str] = None
    user_id: Optional[str] = None
    email: Optional[str] = None
    error: Optional[str] = None
    error_code: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary, excluding None values."""
        result = {"success": self.success}
        if self.success:
            if self.tokens:
                result["tokens"] = self.tokens
            if self.display_name:
                result["display_name"] = self.display_name
            if self.user_id:
                result["user_id"] = self.user_id
            if self.email:
                result["email"] = self.email
        else:
            if self.error:
                result["error"] = self.error
            if self.error_code:
                result["error_code"] = self.error_code
        return result


def coros_login(email: str, password: str) -> LoginResult:
    """
    Authenticate with COROS Training Hub.

    Args:
        email: COROS account email
        password: COROS account password

    Returns:
        LoginResult with tokens if successful, error details if not
    """
    try:
        client = CorosClient(email=email, password=password)
        user_info = client.login()

        # Export tokens for session persistence
        tokens = client.export_token()

        return LoginResult(
            success=True,
            tokens=tokens,
            display_name=user_info.nickname,
            user_id=user_info.user_id,
            email=user_info.email,
        )

    except ValueError as e:
        error_msg = str(e)
        # Parse common COROS error messages
        if "1030" in error_msg or "password" in error_msg.lower():
            return LoginResult(
                success=False,
                error="Invalid email or password",
                error_code="INVALID_CREDENTIALS",
            )
        elif "1001" in error_msg or "account" in error_msg.lower():
            return LoginResult(
                success=False,
                error="Account not found",
                error_code="ACCOUNT_NOT_FOUND",
            )
        else:
            return LoginResult(
                success=False,
                error=f"Login failed: {error_msg}",
                error_code="LOGIN_ERROR",
            )

    except Exception as e:
        return LoginResult(
            success=False,
            error=f"Unexpected error: {str(e)}",
            error_code="UNEXPECTED_ERROR",
        )
