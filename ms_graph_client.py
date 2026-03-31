"""Microsoft Graph API client for directory lookups."""

import logging

import httpx

logger = logging.getLogger(__name__)

USER_PROPERTIES = (
    "id,displayName,givenName,surname,mail,userPrincipalName,"
    "jobTitle,department,officeLocation,businessPhones,mobilePhone"
)


class GraphClient:
    """Async client for Microsoft Graph API."""

    def __init__(self, base_url: str = "https://graph.microsoft.com/beta"):
        self.base_url = base_url.rstrip("/")

    async def get(self, endpoint: str, token: str, params: dict | None = None) -> dict:
        """Make a GET request to Graph API."""
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        url = f"{self.base_url}{endpoint}"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params)

            if response.status_code == 404:
                return {"value": []}
            if response.status_code != 200:
                logger.error(f"Graph API error {response.status_code}: {response.text[:200]}")
                response.raise_for_status()

            return response.json()

    async def find_user(self, token: str, query: str) -> list[dict]:
        """Search for a user by email, name, or UPN."""
        safe_query = query.replace("'", "''")

        if "@" in query:
            filter_str = (
                f"mail eq '{safe_query}' or "
                f"userPrincipalName eq '{safe_query}'"
            )
        else:
            filter_str = (
                f"startswith(displayName, '{safe_query}') or "
                f"startswith(surname, '{safe_query}') or "
                f"startswith(givenName, '{safe_query}')"
            )

        result = await self.get(
            "/users",
            token,
            params={
                "$filter": filter_str,
                "$select": USER_PROPERTIES,
                "$top": "10",
            },
        )
        return result.get("value", [])

    async def get_user_groups(self, token: str, user_id: str) -> list[dict]:
        """Get a user's group memberships."""
        result = await self.get(
            f"/users/{user_id}/memberOf",
            token,
            params={"$select": "id,displayName,groupTypes,mailEnabled"},
        )
        return [
            m for m in result.get("value", [])
            if m.get("@odata.type") == "#microsoft.graph.group"
        ]
