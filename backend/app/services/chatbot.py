"""Empathetic citizen assistant -- a tool-calling agent, not vector RAG.

This platform's knowledge is almost entirely structured DB rows (villages, issues,
works, allocations, transparency figures), not prose documents -- a shallow embedding
index over tabular data would paraphrase-and-hallucinate. Giving the model *tools* that
query the real DB directly (app.services.chatbot_tools) keeps every answer traceable to
a real row, the same grounding philosophy as app.services.explain's numeric-verification
guardrail, applied to a different (free-form, multi-turn) shape: there's no regex check
here because the grounding comes from the model only ever seeing real tool output, not
from checking its prose afterward.

Provider order is Claude first, NVIDIA NIM second -- the reverse of app.services.explain's
NVIDIA-first house style. That order is deliberate for this specific feature: a
multi-round tool-calling agent loop needs reliable structured tool-call output more than
it needs the cheaper base model, and Anthropic's tool-use API is the more predictable of
the two for that. Falls back to a plain apology (no template narrative is possible for
free-form chat) if both providers are unavailable or fail.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.chatbot_tools import TOOL_SCHEMAS, execute_tool

MAX_TOOL_ROUNDS = 5
CLAUDE_MODEL = "claude-sonnet-5"

SYSTEM_PROMPT = """You are a warm, patient assistant helping citizens of Bagalkot constituency (Karnataka) report problems to their MP's office and understand what happens to their reports. Many people you talk to may be stressed, frustrated, or unfamiliar with government processes -- be clear, reassuring, and speak plainly, avoiding jargon and acronyms unless you explain them.

You have tools to look up real data: village facts, citizen issues, ranked development works, budget justification, a citizen's own report status, and constituency-wide transparency figures. You can also file a new grievance on a citizen's behalf, but only after they've clearly described their issue in their own words AND explicitly confirmed they want it submitted.

Hard rule: every factual or numeric claim you make must come from a tool result you actually received in this conversation. If no tool covers what's being asked, say so plainly rather than guessing, estimating, or inventing a fact, number, or village name. If a lookup finds nothing, say that directly.

Keep replies concise and conversational -- this is a chat, not a report. Reply in the language the citizen is writing in when reasonable."""

FALLBACK_REPLY = "I'm sorry, I'm not able to help right now. Please try again in a moment, or use the Report an Issue form directly."


@dataclass
class ChatResult:
    reply: str
    sources: list[str]


def _claude_tools() -> list[dict]:
    return [{"name": t["name"], "description": t["description"], "input_schema": t["parameters"]} for t in TOOL_SCHEMAS]


def _nvidia_tools() -> list[dict]:
    return [
        {"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["parameters"]}}
        for t in TOOL_SCHEMAS
    ]


def _try_claude_turn(db: Session, messages: list[dict]) -> ChatResult | None:
    if not settings.anthropic_api_key:
        return None
    try:
        import anthropic
    except ImportError:
        return None

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        conversation: list[dict] = [{"role": m["role"], "content": m["content"]} for m in messages]
        sources: list[str] = []

        for _ in range(MAX_TOOL_ROUNDS):
            response = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                tools=_claude_tools(),
                messages=conversation,
            )
            if response.stop_reason != "tool_use":
                text = "".join(b.text for b in response.content if b.type == "text").strip()
                return ChatResult(reply=text or FALLBACK_REPLY, sources=sources)

            conversation.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = execute_tool(db, block.name, block.input)
                    sources.append(block.name)
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(result, default=str)})
            conversation.append({"role": "user", "content": tool_results})

        return ChatResult(reply="I looked into a few things but couldn't finish in time -- could you ask that again, maybe more specifically?", sources=sources)
    except Exception:
        return None


def _try_nvidia_turn(db: Session, messages: list[dict]) -> ChatResult | None:
    if not settings.nvidia_nim_api_key:
        return None
    try:
        import openai
    except ImportError:
        return None

    try:
        client = openai.OpenAI(api_key=settings.nvidia_nim_api_key, base_url="https://integrate.api.nvidia.com/v1")
        conversation: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}] + [
            {"role": m["role"], "content": m["content"]} for m in messages
        ]
        sources: list[str] = []

        for _ in range(MAX_TOOL_ROUNDS):
            response = client.chat.completions.create(
                model=settings.nvidia_model,
                max_tokens=2500,
                messages=conversation,
                tools=_nvidia_tools(),
            )
            message = response.choices[0].message
            if not message.tool_calls:
                return ChatResult(reply=(message.content or "").strip() or FALLBACK_REPLY, sources=sources)

            conversation.append({"role": "assistant", "content": message.content, "tool_calls": message.tool_calls})
            for call in message.tool_calls:
                args = json.loads(call.function.arguments or "{}")
                result = execute_tool(db, call.function.name, args)
                sources.append(call.function.name)
                conversation.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result, default=str)})

        return ChatResult(reply="I looked into a few things but couldn't finish in time -- could you ask that again, maybe more specifically?", sources=sources)
    except Exception:
        return None


def handle_turn(db: Session, messages: list[dict]) -> ChatResult:
    """messages: [{"role": "user"|"assistant", "content": str}, ...] -- the full
    conversation so far, resent each turn (stateless server, per the approved plan)."""
    result = _try_claude_turn(db, messages)
    if result is not None:
        return result
    result = _try_nvidia_turn(db, messages)
    if result is not None:
        return result
    return ChatResult(reply=FALLBACK_REPLY, sources=[])
