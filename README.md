# COROS MCP Server

MCP server to access COROS Training Hub data via the Model Context Protocol.

## Architecture

```
coros_mcp/
├── __init__.py          # Main entry, FastMCP server
├── coros_client.py      # COROS API client (ported from coros-connect)
├── coros_platform.py    # Login function with LoginResult
├── client_factory.py    # get_client(ctx), token serialization
├── auth_tool.py         # coros_login, set_coros_session, coros_logout
│                        # + get_user_name, get_available_features
└── activities.py        # Activity tools (list, details, download)
```

## Session Pattern

Uses FastMCP Context for session-based authentication:

```python
from mcp.server.fastmcp import Context
from coros_mcp.client_factory import get_client

@app.tool()
async def get_activities(ctx: Context, days: int = 7) -> str:
    """Get recent activities."""
    client = await get_client(ctx)  # Gets client from session
    return json.dumps(client.get_activities_list())
```

## Available Tools

### Authentication
- `coros_login_tool` - Login with COROS credentials
- `set_coros_session` - Restore session from tokens
- `coros_logout` - Clear session

### User Info
- `get_user_name` - Get display name and user ID
- `get_available_features` - List available data features

### Activities
- `get_activities` - List activities with date filters
- `get_activity_details` - Detailed activity data
- `get_activity_download_url` - Download URL for FIT/TCX/GPX/CSV
- `get_activities_summary` - Aggregated stats over N days

## Limitations

COROS Training Hub API is limited compared to Garmin:
- No sleep data
- No HRV/stress/body battery data
- No daily health metrics

For those metrics, use Garmin MCP or request a data export from COROS support.

## Installation

```bash
cd mcp-servers/coros_mcp
uv pip install -e .
```

## Usage

```bash
coros-mcp
```

Or in Python:

```python
from coros_mcp import main
main()
```

## Credits

Based on [coros-connect](https://github.com/jmn8718/coros-connect) TypeScript library.

**Note:** This uses a non-public API from COROS Training Hub that could break anytime.
