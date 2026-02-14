"""
COROS Platform login functionality.

Provides the LoginResult interface matching the garmin_mcp pattern.
"""

from dataclasses import dataclass
from typing import Optional

from coros_mcp.sdk.client import CorosClient
from coros_mcp.sdk import auth as sdk_auth


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
    details: Optional[dict] = None

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
            if self.details:
                result["details"] = self.details
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
        # Use EU region by default (most users are in Europe)
        client = CorosClient(email=email, password=password, region="eu")
        user_info = sdk_auth.login(client)

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
                details={
                    "message": "The email or password you entered is incorrect",
                    "context": "COROS server rejected the login credentials",
                    "solution": "Double-check your email and password:\n  • Verify you're using your COROS account email\n  • Check for typos in your password\n  • Try logging in at coros.com to verify credentials",
                    "common_issues": [
                        "Using wrong email (must be COROS account email)",
                        "Copy-paste adding extra spaces",
                        "Password recently changed but using old password",
                    ],
                },
            )
        elif "1001" in error_msg or "account" in error_msg.lower():
            return LoginResult(
                success=False,
                error="Account not found",
                error_code="ACCOUNT_NOT_FOUND",
                details={
                    "message": "No COROS account found with this email address",
                    "context": "COROS server reports this email is not registered",
                    "solution": "Verify your COROS account:\n  • Check if you have a COROS account at coros.com\n  • Verify the email address is correct\n  • Create a COROS account if you don't have one yet",
                },
            )
        else:
            return LoginResult(
                success=False,
                error=f"Login failed: {error_msg}",
                error_code="LOGIN_ERROR",
                details={
                    "message": "COROS login failed with an error",
                    "context": error_msg,
                    "solution": "Try again in a few moments. If the problem persists:\n  • Verify your credentials at coros.com\n  • Check if COROS is experiencing outages\n  • Contact COROS support if needed",
                },
            )

    except Exception as e:
        return LoginResult(
            success=False,
            error=f"Unexpected error: {str(e)}",
            error_code="UNEXPECTED_ERROR",
            details={
                "message": "An unexpected error occurred during COROS authentication",
                "context": str(e),
                "solution": "Please try again. If the problem persists:\n  • Check the error message above for clues\n  • Verify your internet connection\n  • Try again later if COROS servers might be down",
            },
        )
