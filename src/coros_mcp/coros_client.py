"""
COROS Training Hub API Client

Python port of the coros-connect TypeScript library.
Based on: https://github.com/jmn8718/coros-connect

This uses a non-public API from COROS Training Hub that could break anytime.
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests


# API Configuration
API_URL = "https://teamapi.coros.com"
FAQ_API_URL = "https://faq.coros.com"
SALT = "9y78gpoERW4lBNYL"


class FileType(Enum):
    """Export file type options."""
    CSV = "0"
    GPX = "1"
    KML = "2"
    TCX = "3"
    FIT = "4"


class STSRegion(Enum):
    """Storage region configuration."""
    EN = "en.prod"
    CN = "cn.prod"
    EU = "eu.prod"


@dataclass
class STSConfig:
    """STS (Security Token Service) configuration."""
    env: str
    bucket: str
    service: str  # 'aws' or 'aliyun'


# Pre-defined STS configurations
STS_CONFIGS = {
    STSRegion.EN: STSConfig(env="en.prod", bucket="coros-s3", service="aws"),
    STSRegion.CN: STSConfig(env="cn.prod", bucket="coros-oss", service="aliyun"),
    STSRegion.EU: STSConfig(env="eu.prod", bucket="eu-coros", service="aws"),
}


@dataclass
class UserInfo:
    """COROS user information."""
    user_id: str
    nickname: str
    email: str
    head_pic: str
    country_code: str
    birthday: int  # YYYYMMDD as number


@dataclass
class Activity:
    """COROS activity summary."""
    label_id: str
    date: int  # YYYYMMDD as number
    name: str
    sport_type: int
    distance: float
    total_time: int
    workout_time: int
    training_load: int
    start_time: int
    end_time: int
    device: str
    image_url: str


class CorosClient:
    """
    COROS Training Hub API Client.

    Implements the same functionality as coros-connect TypeScript library.
    """

    def __init__(self, email: str = None, password: str = None):
        """
        Initialize the COROS client.

        Args:
            email: COROS account email
            password: COROS account password
        """
        self._email = email
        self._password = password
        self._access_token: Optional[str] = None
        self._user_info: Optional[UserInfo] = None

        self._api_url = API_URL
        self._faq_api_url = FAQ_API_URL
        self._salt = SALT
        self._sts_config = STS_CONFIGS[STSRegion.EN]
        self._sign = "E34EF0E34A498A54A9C3EAEFC12B7CAF"
        self._app_id = "1660188068672619112"

        self._session = requests.Session()

    @property
    def access_token(self) -> Optional[str]:
        """Get the current access token."""
        return self._access_token

    @property
    def user_info(self) -> Optional[UserInfo]:
        """Get the current user info."""
        return self._user_info

    @property
    def is_logged_in(self) -> bool:
        """Check if client is authenticated."""
        return self._access_token is not None

    def config(
        self,
        api_url: str = None,
        app_id: str = None,
        sign: str = None,
        salt: str = None,
        faq_api_url: str = None,
        sts_region: STSRegion = None,
    ):
        """
        Configure the client.

        Args:
            api_url: Custom API URL
            app_id: Custom app ID
            sign: Custom sign value
            salt: Custom salt value
            faq_api_url: Custom FAQ API URL
            sts_region: STS region configuration
        """
        if api_url:
            self._api_url = api_url
        if app_id:
            self._app_id = app_id
        if sign:
            self._sign = sign
        if salt:
            self._salt = salt
        if faq_api_url:
            self._faq_api_url = faq_api_url
        if sts_region:
            if sts_region == STSRegion.CN:
                raise ValueError("Aliyun (CN) provider not implemented")
            self._sts_config = STS_CONFIGS[sts_region]

    def _md5_hash(self, value: str) -> str:
        """Generate MD5 hash of a string."""
        return hashlib.md5(value.encode()).hexdigest()

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Dict = None,
        json_data: Dict = None,
        require_auth: bool = True,
    ) -> Dict[str, Any]:
        """
        Make an API request.

        Args:
            method: HTTP method (GET/POST)
            endpoint: API endpoint
            params: Query parameters
            json_data: JSON body data
            require_auth: Whether authentication is required

        Returns:
            API response data

        Raises:
            RuntimeError: If not logged in but auth required
            ValueError: If API returns an error
        """
        if require_auth and not self._access_token:
            raise RuntimeError("Not logged in. Call login() first.")

        headers = {
            "Content-Type": "application/json",
        }
        if self._access_token:
            headers["accessToken"] = self._access_token

        # Add yfheader with userId for all authenticated requests
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
            raise ValueError(data.get("message", "Unknown API error"))

        return data

    def login(self, email: str = None, password: str = None) -> UserInfo:
        """
        Authenticate with COROS.

        Args:
            email: COROS account email (uses stored if not provided)
            password: COROS account password (uses stored if not provided)

        Returns:
            UserInfo object with user details

        Raises:
            ValueError: If credentials are missing or invalid
        """
        email = email or self._email
        password = password or self._password

        if not email or not password:
            raise ValueError("Missing credentials")

        self._email = email
        self._password = password

        response = self._make_request(
            "POST",
            "account/login",
            json_data={
                "account": email,
                "accountType": 2,
                "pwd": self._md5_hash(password),
            },
            require_auth=False,
        )

        data = response["data"]
        self._access_token = data["accessToken"]

        self._user_info = UserInfo(
            user_id=data["userId"],
            nickname=data["nickname"],
            email=data["email"],
            head_pic=data.get("headPic", ""),
            country_code=data.get("countryCode", ""),
            birthday=data.get("birthday", 0),
        )

        return self._user_info

    def get_account(self) -> UserInfo:
        """
        Get current account information.

        Returns:
            UserInfo object with user details
        """
        response = self._make_request("GET", "account/query")
        data = response["data"]

        self._user_info = UserInfo(
            user_id=data["userId"],
            nickname=data["nickname"],
            email=data["email"],
            head_pic=data.get("headPic", ""),
            country_code=data.get("countryCode", ""),
            birthday=data.get("birthday", 0),
        )

        return self._user_info

    def get_activities_list(
        self,
        page: int = 1,
        size: int = 20,
        from_date: date = None,
        to_date: date = None,
        mode_list: str = "",
    ) -> Dict[str, Any]:
        """
        Get list of activities.

        Args:
            page: Page number (1-indexed)
            size: Number of activities per page
            from_date: Start date filter
            to_date: End date filter
            mode_list: Activity mode filter

        Returns:
            Dictionary with activity list data including:
            - count: Total number of activities
            - totalPage: Total pages
            - pageNumber: Current page
            - dataList: List of activity summaries
        """
        params = {
            "size": str(size),
            "pageNumber": str(page),
        }

        if from_date:
            params["startDay"] = from_date.strftime("%Y%m%d")
        if to_date:
            params["endDay"] = to_date.strftime("%Y%m%d")
        if mode_list:
            params["modeList"] = mode_list

        response = self._make_request("GET", "activity/query", params=params)
        return response["data"]

    def get_activity_details(self, activity_id: str) -> Dict[str, Any]:
        """
        Get detailed information about an activity.

        Args:
            activity_id: The activity's labelId

        Returns:
            Dictionary with detailed activity data including:
            - summary: Activity summary metrics
            - frequencyList: GPS/heart rate data points
            - lapList: Lap information
            - graphList: Chart data
            - zoneList: Heart rate/power zones
            - weather: Weather conditions
            - etc.
        """
        response = self._make_request(
            "POST",
            "activity/detail/query",
            params={
                "labelId": activity_id,
                "sportType": "100",
            },
        )
        return response["data"]

    def get_activity_download_url(
        self,
        activity_id: str,
        file_type: FileType = FileType.FIT,
    ) -> str:
        """
        Get download URL for an activity file.

        Args:
            activity_id: The activity's labelId
            file_type: Export file format

        Returns:
            URL to download the activity file
        """
        response = self._make_request(
            "POST",
            "activity/detail/download",
            params={
                "labelId": activity_id,
                "sportType": "100",
                "fileType": file_type.value,
            },
        )
        return response["data"]["fileUrl"]

    def delete_activity(self, activity_id: str) -> bool:
        """
        Delete an activity.

        Args:
            activity_id: The activity's labelId

        Returns:
            True if deleted successfully
        """
        self._make_request(
            "GET",
            "activity/delete",
            params={"labelId": activity_id},
        )
        return True

    # Token serialization for session persistence

    def export_token(self) -> str:
        """
        Export the access token for session persistence.

        Returns:
            JSON string with token and user info
        """
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
        """
        Load a previously exported token.

        Args:
            token_data: JSON string from export_token()
        """
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

    def export_token_to_file(self, directory_path: str) -> None:
        """
        Export token to a file.

        Args:
            directory_path: Directory to save the token file
        """
        path = Path(directory_path)
        path.mkdir(parents=True, exist_ok=True)

        token_file = path / "token.json"
        token_file.write_text(self.export_token())

    def load_token_from_file(self, directory_path: str) -> None:
        """
        Load token from a file.

        Args:
            directory_path: Directory containing the token file
        """
        path = Path(directory_path)
        token_file = path / "token.json"

        if not token_file.exists():
            raise FileNotFoundError(f"Token file not found: {token_file}")

        self.load_token(token_file.read_text())

    def logout(self) -> None:
        """Clear the session."""
        self._access_token = None
        self._user_info = None
