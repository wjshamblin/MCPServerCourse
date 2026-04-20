"""Business logic for directory operations.

This module used to orchestrate the OBO exchange itself. Now the OBO flow
is handled upstream by `EntraOBOToken` (see server.py); this layer just
takes a ready-to-use Microsoft Graph token and calls Graph with it.
"""

import logging

from ms_graph_client import GraphClient

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
    """Thin coordinator for Microsoft Graph directory calls."""

    def __init__(self, graph: GraphClient):
        self.graph = graph

    async def find_user(self, graph_token: str, query: str) -> list[dict]:
        """Search for users in the directory using a pre-exchanged Graph token."""
        logger.info(f"Finding user: {sanitize_for_log(query)}")
        return await self.graph.find_user(graph_token, query)

    async def get_user_groups(self, graph_token: str, user_id: str) -> list[dict]:
        """Get a user's group memberships using a pre-exchanged Graph token."""
        logger.info(f"Getting groups for: {sanitize_for_log(user_id)}")
        return await self.graph.get_user_groups(graph_token, user_id)
