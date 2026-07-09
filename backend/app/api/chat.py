"""POST /chat -- the citizen assistant. See app.services.chatbot for the agent loop and
grounding rationale.

Stateless: the client resends the full message history each turn (no server-side session
table) -- the same trade-off the rest of this read-mostly API makes elsewhere, and it
means a page refresh doesn't strand a conversation server-side. Rate-limited like
POST /submissions, but more generously -- a back-and-forth conversation naturally makes
more requests than a single form submission.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.rate_limit import limiter
from app.services.chatbot import handle_turn

router = APIRouter(prefix="/chat", tags=["chat"])

MAX_MESSAGES = 40
MAX_MESSAGE_LENGTH = 4000


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., min_length=1)


@router.post("")
@limiter.limit("30/hour")
def post_chat(request: Request, body: ChatRequest, db: Session = Depends(get_db)) -> dict:
    if len(body.messages) > MAX_MESSAGES:
        raise HTTPException(status_code=422, detail=f"Conversation too long (max {MAX_MESSAGES} messages) -- please start a new chat.")
    for m in body.messages:
        if m.role not in ("user", "assistant"):
            raise HTTPException(status_code=422, detail="message role must be 'user' or 'assistant'")
        if len(m.content) > MAX_MESSAGE_LENGTH:
            raise HTTPException(status_code=422, detail=f"message content must be at most {MAX_MESSAGE_LENGTH} characters")

    result = handle_turn(db, [m.model_dump() for m in body.messages])
    return {"reply": result.reply, "sources": result.sources}
