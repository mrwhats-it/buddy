from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import load_config, save_config
from .content_extract import extract_from_url
from .llm_client import LLMClient
from .supermemory_client import (
    BUDDY_CONTAINER_TAG,
    SupermemoryClient,
    build_save_metadata,
    result_text,
)
from .supermemory_installer import check_state, guidance_for

app = FastAPI(title="Buddy backend")

# Extension pages run under chrome-extension:// origins; allow any origin
# since this server only ever binds to localhost.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class SaveRequest(BaseModel):
    content: str
    is_link: bool = False
    comment: str | None = None
    page_title: str | None = None


class SearchRequest(BaseModel):
    query: str
    limit: int = 8


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


class TitleRequest(BaseModel):
    prompt: str


class ConfigUpdate(BaseModel):
    supermemory_url: str | None = None
    supermemory_api_key: str | None = None
    provider: str | None = None
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None


def _supermemory_client() -> SupermemoryClient:
    cfg = load_config()
    return SupermemoryClient(cfg["supermemory_url"], cfg["supermemory_api_key"])


def _llm_client() -> LLMClient:
    cfg = load_config()
    return LLMClient(cfg["llm_base_url"], cfg["llm_api_key"], cfg["llm_model"])


@app.get("/health")
async def health():
    cfg = load_config()
    state = await check_state(cfg["supermemory_url"], cfg["supermemory_api_key"])
    return {
        "backend": "ok",
        "supermemory": "ok" if state == "ready" else state,
        "supermemory_guidance": None if state == "ready" else guidance_for(state, cfg["supermemory_url"]),
        "llm_configured": bool(cfg["llm_base_url"] and cfg["llm_api_key"] and cfg["llm_model"]),
    }


@app.get("/config")
async def get_config():
    cfg = load_config()
    cfg["llm_api_key"] = "set" if cfg["llm_api_key"] else ""
    cfg["supermemory_api_key"] = "set" if cfg["supermemory_api_key"] else ""
    return cfg


@app.post("/config")
async def set_config(update: ConfigUpdate):
    return save_config(update.model_dump())


@app.post("/save")
async def save(req: SaveRequest):
    content = req.content
    source_url = None
    title = req.page_title

    if req.is_link:
        source_url = req.content
        try:
            content, extracted_title = await extract_from_url(req.content)
            title = extracted_title or title
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Could not fetch/extract link: {exc}")

    metadata = build_save_metadata(source_url, title, req.comment)
    try:
        result = await _supermemory_client().add_document(
            content=content,
            container_tags=[BUDDY_CONTAINER_TAG],
            metadata=metadata,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not reach supermemory: {exc}")

    return {"saved": True, "metadata": metadata, "supermemory": result}


@app.post("/search")
async def search(req: SearchRequest):
    try:
        results = await _supermemory_client().search(req.query, req.limit)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not reach supermemory: {exc}")
    return {"results": results}


@app.post("/chat")
async def chat(req: ChatRequest):
    last_user_message = next(
        (m.content for m in reversed(req.messages) if m.role == "user"), ""
    )

    try:
        memories = await _supermemory_client().search(last_user_message, limit=8)
    except Exception:
        memories = []

    context_block = "\n\n".join(f"- {result_text(m)}" for m in memories)

    system_prompt = (
        "You are Buddy, a personal assistant that answers questions grounded in "
        "the user's saved memories. Use the context below if relevant; if it "
        "doesn't contain the answer, say so rather than making things up.\n\n"
        f"Saved context:\n{context_block or '(no relevant saved memories found)'}"
    )

    llm_messages = [{"role": "system", "content": system_prompt}] + [
        m.model_dump() for m in req.messages
    ]

    try:
        reply = await _llm_client().chat(llm_messages)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM request failed: {exc}")

    return {"reply": reply, "grounded_on": len(memories)}


@app.post("/title")
async def title(req: TitleRequest):
    """Generate a short (<=6 words) title for a chat from the user's first prompt.
    Runs in parallel with /chat from the extension, so keep it cheap and fast."""
    system = (
        "You generate very short chat titles. Reply with ONLY the title itself "
        "— no quotes, no punctuation at the end, no prefix like 'Title:'. "
        "Maximum 6 words. Title case."
    )
    try:
        reply = await _llm_client().chat(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": req.prompt},
            ]
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM request failed: {exc}")
    cleaned = reply.strip().strip('"').strip("'").splitlines()[0][:60]
    return {"title": cleaned}
