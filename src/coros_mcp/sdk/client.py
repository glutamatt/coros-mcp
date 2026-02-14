"""
COROS Training Hub HTTP Client.

Handles HTTP transport, authentication, region routing, and error handling.
All domain-specific logic lives in the sibling modules (auth, activities, etc.).

Based on: https://github.com/jmn8718/coros-connect
"""

import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests

from coros_mcp.sdk.types import STSRegion

logger = logging.getLogger(__name__)

# Regional API URLs
API_URL = "https://teamapi.coros.com"
API_URL_EU = "https://teameuapi.coros.com"
API_URL_CN = "https://teamapi.coros.com.cn"

SALT = "9y78gpoERW4lBNYL"


@dataclass
class UserInfo:
    """COROS user information."""
    user_id: str
    nickname: str
    email: str
    head_pic: str
    country_code: str
    birthday: int  # YYYYMMDD as number


class CorosClient:
    """
    COROS Training Hub HTTP transport.

    Handles authentication, headers, region routing, and request/response parsing.
    Domain-specific endpoint calls are in sibling modules (sdk.auth, sdk.activities, etc.).
    """

    def __init__(self, email: str = None, password: str = None, region: str = "eu"):
        self._email = email
        self._password = password
        self._access_token: Optional[str] = None
        self._user_info: Optional[UserInfo] = None

        # Set API URL based on region
        if region == "eu":
            self._api_url = API_URL_EU
        elif region == "cn":
            self._api_url = API_URL_CN
        else:  # global
            self._api_url = API_URL

        self._session = requests.Session()

    @property
    def access_token(self) -> Optional[str]:
        return self._access_token

    @property
    def user_info(self) -> Optional[UserInfo]:
        return self._user_info

    @user_info.setter
    def user_info(self, value: UserInfo):
        self._user_info = value

    @property
    def is_logged_in(self) -> bool:
        return self._access_token is not None

    def make_request(
        self,
        method: str,
        endpoint: str,
        params: Dict = None,
        json_data: Dict = None,
        require_auth: bool = True,
    ) -> Dict[str, Any]:
        """
        Make an authenticated API request.

        Args:
            method: HTTP method (GET/POST)
            endpoint: API endpoint path (e.g. "activity/query")
            params: Query parameters
            json_data: JSON body data
            require_auth: Whether authentication is required

        Returns:
            Full API response dict (including result, message, data)

        Raises:
            RuntimeError: If not logged in but auth required
            ValueError: If API returns a non-success result code
        """
        if require_auth and not self._access_token:
            raise RuntimeError("Not logged in. Call login() first.")

        headers = {"Content-Type": "application/json"}
        if self._access_token:
            headers["accessToken"] = self._access_token
        if self._user_info and self._user_info.user_id:
            headers["yfheader"] = json.dumps({"userId": self._user_info.user_id})

        url = f"{self._api_url}/{endpoint}"

        if method.upper() == "GET":
            response = self._session.get(url, headers=headers, params=params)
        else:
            response = self._session.post(url, headers=headers, params=params, json=json_data)

        response.raise_for_status()
        data = response.json()

        if data.get("result") != "0000":
            raise ValueError(
                f"{data.get('message', 'Unknown API error')} "
                f"(apiCode={data.get('apiCode')}, result={data.get('result')})"
            )

        return data

    @staticmethod
    def md5_hash(value: str) -> str:
        """Generate MD5 hash of a string."""
        return hashlib.md5(value.encode()).hexdigest()

    # ── Token serialization ──────────────────────────────────────────────

    def export_token(self) -> str:
        """Export access token and user info as JSON string."""
        if not self._access_token:
            raise RuntimeError("Not logged in. Call login() first.")

        return json.dumps({
            "access_token": self._access_token,
            "user_info": {
                "user_id": self._user_info.user_id,
                "nickname": self._user_info.nickname,
                "email": self._user_info.email,
                "head_pic": self._user_info.head_pic,
                "country_code": self._user_info.country_code,
                "birthday": self._user_info.birthday,
            } if self._user_info else None,
        })

    def load_token(self, token_data: str) -> None:
        """Load a previously exported token."""
        data = json.loads(token_data)
        self._access_token = data["access_token"]

        if data.get("user_info"):
            ui = data["user_info"]
            self._user_info = UserInfo(
                user_id=ui["user_id"],
                nickname=ui["nickname"],
                email=ui["email"],
                head_pic=ui.get("head_pic", ""),
                country_code=ui.get("country_code", ""),
                birthday=ui.get("birthday", 0),
            )

    def logout(self) -> None:
        """Clear the session."""
        self._access_token = None
        self._user_info = None
