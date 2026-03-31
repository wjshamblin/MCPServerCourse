"""
Azure AD On-Behalf-Of (OBO) Token Exchange

Exchanges a user's MCP access token for a Microsoft Graph API token,
allowing the server to call Graph on behalf of the authenticated user.
"""

import hashlib
import logging
import time
from collections import OrderedDict
from threading import Lock

import httpx

logger = logging.getLogger(__name__)


class OBOTokenCache:
    """Thread-safe cache for OBO tokens with TTL and LRU eviction."""

    def __init__(self, ttl_seconds: int = 3000, max_size: int = 500):
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._cache: OrderedDict[str, tuple[str, float, float]] = OrderedDict()
        self._lock = Lock()

    def _hash_key(self, assertion: str) -> str:
        return hashlib.sha256(assertion.encode()).hexdigest()[:32]

    def get(self, assertion: str) -> str | None:
        key = self._hash_key(assertion)
        with self._lock:
            if key in self._cache:
                token, timestamp, expires_at = self._cache[key]
                now = time.time()
                if now - timestamp < self.ttl_seconds and now < expires_at:
                    self._cache.move_to_end(key)
                    return token
                del self._cache[key]
        return None

    def set(self, assertion: str, token: str, expires_in: int = 3600) -> None:
        key = self._hash_key(assertion)
        with self._lock:
            if key in self._cache:
                del self._cache[key]
            if len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)
            self._cache[key] = (token, time.time(), time.time() + expires_in - 60)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()


class OBOExchangeError(Exception):
    pass


class OBOTokenExchange:
    """Handles Azure AD On-Behalf-Of token exchange."""

    def __init__(self, client_id: str, client_secret: str, token_endpoint: str,
                 graph_scopes: str, cache_ttl: int = 3000):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_endpoint = token_endpoint
        self.graph_scopes = graph_scopes
        self._cache = OBOTokenCache(ttl_seconds=cache_ttl)

    async def exchange(self, user_assertion: str) -> str:
        """Exchange user's MCP token for a Graph API token."""
        cached = self._cache.get(user_assertion)
        if cached:
            return cached

        logger.info("Performing OBO token exchange")

        data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "assertion": user_assertion,
            "scope": self.graph_scopes,
            "requested_token_use": "on_behalf_of",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_endpoint,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code != 200:
                error = response.json()
                msg = error.get("error_description", error.get("error", "Unknown"))
                logger.error(f"OBO exchange failed: {msg}")
                raise OBOExchangeError(f"Token exchange failed: {msg}")

            result = response.json()
            token = result["access_token"]
            expires_in = result.get("expires_in", 3600)
            self._cache.set(user_assertion, token, expires_in)
            return token
