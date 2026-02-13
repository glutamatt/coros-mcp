"""
Spec verification test fixtures.

These tests hit the REAL COROS API to validate that response shapes
match docs/coros-api-spec.md. They require a valid token.

Provide credentials via environment variables:
  COROS_TOKEN_JSON  = exported token JSON (from CorosClient.export_token())
  — OR —
  COROS_EMAIL       = account email
  COROS_PASSWORD    = account password
  COROS_REGION      = eu (default) | global | cn

Run: pytest tests/spec/ -v
"""

import json
import os

import pytest
import requests


BASE_URLS = {
    "eu": "https://teameuapi.coros.com",
    "global": "https://teamapi.coros.com",
    "cn": "https://teamapi.coros.com.cn",
}


def _login(email: str, password: str, base_url: str) -> dict:
    """Login and return {access_token, user_id}."""
    import hashlib

    pwd_hash = hashlib.md5(password.encode()).hexdigest()
    resp = requests.post(
        f"{base_url}/account/login",
        headers={"Content-Type": "application/json"},
        json={"account": email, "accountType": 2, "pwd": pwd_hash},
    )
    resp.raise_for_status()
    data = resp.json()
    assert data["result"] == "0000", f"Login failed: {data}"
    return {
        "access_token": data["data"]["accessToken"],
        "user_id": data["data"]["userId"],
    }


@pytest.fixture(scope="session")
def coros_creds():
    """
    Returns dict with keys: access_token, user_id, base_url.
    Skips all spec tests if no credentials are available.
    """
    region = os.environ.get("COROS_REGION", "eu")
    base_url = BASE_URLS.get(region, BASE_URLS["eu"])

    token_json = os.environ.get("COROS_TOKEN_JSON")
    if token_json:
        parsed = json.loads(token_json)
        return {
            "access_token": parsed["access_token"],
            "user_id": parsed["user_info"]["user_id"],
            "base_url": base_url,
        }

    email = os.environ.get("COROS_EMAIL")
    password = os.environ.get("COROS_PASSWORD")
    if email and password:
        creds = _login(email, password, base_url)
        creds["base_url"] = base_url
        return creds

    pytest.skip("No COROS credentials: set COROS_TOKEN_JSON or COROS_EMAIL+COROS_PASSWORD")


@pytest.fixture(scope="session")
def auth_headers(coros_creds):
    """Standard auth headers for COROS API calls."""
    return {
        "Content-Type": "application/json",
        "accessToken": coros_creds["access_token"],
        "yfheader": json.dumps({"userId": coros_creds["user_id"]}),
    }


@pytest.fixture(scope="session")
def base_url(coros_creds):
    return coros_creds["base_url"]
