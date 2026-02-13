"""
COROS authentication SDK functions.

See docs/coros-api-spec.md § Auth.
"""

from typing import Dict, Any

from coros_mcp.sdk.client import CorosClient, UserInfo


def login(client: CorosClient, email: str = None, password: str = None) -> UserInfo:
    """
    Authenticate with COROS.

    POST account/login

    Args:
        client: CorosClient instance
        email: COROS account email (uses client's stored email if not provided)
        password: COROS account password (uses client's stored email if not provided)

    Returns:
        UserInfo with user details

    Raises:
        ValueError: If credentials are missing or invalid
    """
    email = email or client._email
    password = password or client._password

    if not email or not password:
        raise ValueError("Missing credentials")

    client._email = email
    client._password = password

    response = client.make_request(
        "POST",
        "account/login",
        json_data={
            "account": email,
            "accountType": 2,
            "pwd": client.md5_hash(password),
        },
        require_auth=False,
    )

    data = response["data"]
    client._access_token = data["accessToken"]

    user_info = UserInfo(
        user_id=data["userId"],
        nickname=data["nickname"],
        email=data["email"],
        head_pic=data.get("headPic", ""),
        country_code=data.get("countryCode", ""),
        birthday=data.get("birthday", 0),
    )
    client._user_info = user_info

    return user_info


def get_account(client: CorosClient) -> UserInfo:
    """
    Get current account information.

    GET account/query

    Returns:
        UserInfo with user details
    """
    response = client.make_request("GET", "account/query")
    data = response["data"]

    user_info = UserInfo(
        user_id=data["userId"],
        nickname=data["nickname"],
        email=data["email"],
        head_pic=data.get("headPic", ""),
        country_code=data.get("countryCode", ""),
        birthday=data.get("birthday", 0),
    )
    client._user_info = user_info

    return user_info


def get_account_full(client: CorosClient) -> Dict[str, Any]:
    """
    Get full account profile including biometrics and training zones.

    GET account/query

    Returns:
        Raw response data dict with user info, zone data, run scores, etc.
    """
    response = client.make_request("GET", "account/query")
    return response["data"]
