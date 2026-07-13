import time

import httpx
from supermemory import AsyncSupermemory

# Everything Buddy saves is tagged with this so we can scope searches to just
# Buddy's own content (an unscoped search doesn't reliably return it).
BUDDY_CONTAINER_TAG = "buddy"


class SupermemoryClient:
    """Wrapper around the official `supermemory` Python SDK, pointed at a
    local self-hosted instance (default http://localhost:6767).
    """

    def __init__(self, base_url: str, api_key: str):
        self._client = AsyncSupermemory(api_key=api_key, base_url=base_url)
        self.base_url = base_url

    async def add_document(self, content: str, container_tags: list[str], metadata: dict) -> dict:
        result = await self._client.add(
            content=content,
            container_tags=container_tags,
            metadata=metadata,
        )
        return result.model_dump() if hasattr(result, "model_dump") else dict(result)

    async def search(self, query: str, limit: int = 8) -> list[dict]:
        # Scope to Buddy's container tag — an unscoped search doesn't reliably
        # return our saved docs.
        result = await self._client.search.documents(
            q=query, limit=limit, container_tags=[BUDDY_CONTAINER_TAG]
        )
        results = getattr(result, "results", None)
        if results is None and isinstance(result, dict):
            results = result.get("results", [])
        return [r.model_dump() if hasattr(r, "model_dump") else r for r in (results or [])]

    async def server_reachable(self) -> bool:
        """True if something is listening and speaking HTTP at base_url,
        regardless of whether our API key is valid. Used to distinguish
        "not running" from "running but unauthenticated"."""
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                await client.get(self.base_url)
            return True
        except httpx.ConnectError:
            return False
        except httpx.HTTPError:
            # Any HTTP-level response (even an error status) means something is listening.
            return True

    async def authenticated(self) -> bool:
        """True if our api_key actually works against the running server."""
        try:
            await self._client.search.documents(q="__buddy_health_check__", limit=1)
            return True
        except Exception:
            return False

    async def health(self) -> bool:
        return await self.authenticated()


def result_text(result: dict) -> str:
    """Pull the human-readable text out of a search result. supermemory returns
    the matched text nested under `chunks[].content`, not as a top-level field."""
    if not isinstance(result, dict):
        return str(result)
    if result.get("content"):
        return str(result["content"])
    chunks = result.get("chunks") or []
    texts = [c.get("content", "") for c in chunks if isinstance(c, dict) and c.get("content")]
    if texts:
        return "\n".join(texts)
    # last resort: title/summary if present, else the raw dict
    return str(result.get("title") or result.get("summary") or result)


def build_save_metadata(source_url: str | None, title: str | None, comment: str | None) -> dict:
    # supermemory's metadata schema rejects null values — every field must be a
    # string/number/bool/array. So omit anything that's None rather than sending it.
    metadata: dict = {"saved_at": int(time.time())}
    if source_url:
        metadata["source_url"] = source_url
    if title:
        metadata["title"] = title
    if comment:
        metadata["comment"] = comment
    return metadata
