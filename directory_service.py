"""Business logic for directory operations."""

import logging

from ms_graph_client import GraphClient
from token_exchange import OBOTokenExchange, OBOExchangeError

logger = logging.getLogger(__name__)


def sanitize_for_log(value: str) -> str:
    """Mask PII in log output."""
    if "@" in value:
        parts = value.split("@")
        return f"{parts[0][:2]}***@{parts[1]}"
    if len(value) > 4:
        return f"{value[:3]}***"
    return "***"


class DirectoryService:
    """Coordinates token exchange and Graph API calls."""

    def __init__(self, obo: OBOTokenExchange, graph: GraphClient):
        self.obo = obo
        self.graph = graph

    async def find_user(self, user_token: str, query: str) -> list[dict]:
        """Search for users in the directory."""
        logger.info(f"Finding user: {sanitize_for_log(query)}")
        graph_token = await self.obo.exchange(user_token)
        return await self.graph.find_user(graph_token, query)

    async def get_user_groups(self, user_token: str, user_id: str) -> list[dict]:
        """Get a user's group memberships."""
        logger.info(f"Getting groups for: {sanitize_for_log(user_id)}")
        graph_token = await self.obo.exchange(user_token)
        return await self.graph.get_user_groups(graph_token, user_id)
