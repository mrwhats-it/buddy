import httpx
import trafilatura


async def extract_from_url(url: str) -> tuple[str, str | None]:
    """Fetch a URL and extract main article content. Returns (content, title)."""
    async with httpx.AsyncClient(timeout=15, follow_redirects=True, headers={
        "User-Agent": "Mozilla/5.0 (compatible; BuddyExtension/0.1)"
    }) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        html = resp.text

    extracted = trafilatura.extract(html, include_comments=False, with_metadata=True)
    metadata = trafilatura.extract_metadata(html)
    title = metadata.title if metadata else None

    if not extracted:
        raise ValueError(f"Could not extract readable content from {url}")

    return extracted, title
