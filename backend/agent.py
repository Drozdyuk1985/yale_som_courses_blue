"""PydanticAI course assistant behind POST /api/chat.

main.py calls run_agent(message) and expects {"reply": str, "tools_used": list[str]}.

Two tools only:
  search_courses - local function tool over data/yale_som_classes.json
  web_search     - OpenAI's native server-side web search (native_tools.WebSearchTool)
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai import Agent, RunContext
from pydantic_ai.capabilities import WebSearch
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider

from models import AgentResult, CourseSearchResult
from tools import MAX_COURSE_RESULTS, search_courses

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
load_dotenv(ROOT / ".env")
load_dotenv(ROOT.parent / ".env")

PROMPT_PATH = HERE / "prompts" / "prompt.md"
AUDIT_PATH = ROOT / "output" / "audit_trail.json"
MODEL_NAME = "gpt-6-astra"
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"


class AgentDeps:
    """Per-run scratchpad for the local tool: what fired, with which args, and what returned."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def record(self, name: str, args: dict[str, Any], summary: str) -> None:
        self.calls.append({"tool": name, "args": args, "result": summary[:400]})


def _system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8") if PROMPT_PATH.exists() else ""


def make_model() -> OpenAIResponsesModel:
    """OpenAI through the Portkey gateway. Responses API: required for native web search."""
    key = os.getenv("PORTKEY_API_KEY")
    if not key:
        raise RuntimeError(
            "PORTKEY_API_KEY is missing. Copy lecture7/.env.example to .env "
            "(in lecture7/ or the parent folder) and add your key."
        )
    client = AsyncOpenAI(
        api_key=key,
        base_url=os.getenv("PORTKEY_BASE_URL", PORTKEY_BASE_URL),
        default_headers={"x-portkey-api-key": key, "x-portkey-provider": "openai"},
    )
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))


def build_agent() -> Agent:
    agent = Agent(
        make_model(),
        deps_type=AgentDeps,
        system_prompt=_system_prompt(),
        retries=2,
        # Native (server-side) OpenAI web search. WebSearch() is native by default;
        # a DuckDuckGo fallback would require an explicit local= argument.
        capabilities=[WebSearch()],
    )

    @agent.tool
    def search_courses_tool(
        ctx: RunContext[AgentDeps],
        query: str | None = None,
        title: str | None = None,
        number: str | None = None,
        faculty: str | None = None,
        category: str | None = None,
        day: str | None = None,
        course_type: str | None = None,
        limit: int = MAX_COURSE_RESULTS,
    ) -> CourseSearchResult:
        """Search the Yale SOM course catalog by title, number, faculty, category or day."""
        result = search_courses(
            query=query,
            title=title,
            number=number,
            faculty=faculty,
            category=category,
            day=day,
            course_type=course_type,
            limit=limit,
        )
        supplied = {
            key: value
            for key, value in {
                "query": query,
                "title": title,
                "number": number,
                "faculty": faculty,
                "category": category,
                "day": day,
                "course_type": course_type,
                "limit": limit,
            }.items()
            if value is not None
        }
        ctx.deps.record(
            "search_courses",
            supplied,
            f"{result.total_matches} matched, returned {result.returned}: "
            + ", ".join(f"{c.number} {c.title}" for c in result.courses[:5]),
        )
        return result

    return agent


def _inspect_messages(messages: list[Any]) -> tuple[list[str], list[dict[str, Any]]]:
    """Pull the model's visible reasoning and any native (server-side) tool calls."""
    thoughts: list[str] = []
    native_calls: list[dict[str, Any]] = []

    for message in messages:
        for part in getattr(message, "parts", []):
            kind = type(part).__name__
            if kind in {"ThinkingPart", "TextPart"}:
                text = str(getattr(part, "content", "") or "").strip()
                if text:
                    thoughts.append(text)
            elif kind == "NativeToolCallPart":
                native_calls.append(
                    {
                        "tool": str(getattr(part, "tool_name", "") or "native_tool"),
                        "args": {"raw": str(getattr(part, "args", "") or "")[:300]},
                        "result": "",
                    }
                )
            elif kind == "NativeToolReturnPart" and native_calls:
                native_calls[-1]["result"] = str(getattr(part, "content", "") or "")[:400]

    return thoughts, native_calls


def _normalise_native(tool_name: str) -> str:
    """Map a provider's native tool name onto the name we report to the UI.

    Only applied to native (server-side) calls: local tools already report their
    own names, and 'search_courses' would otherwise be caught by a 'search' match.
    """
    return "web_search" if "search" in tool_name.lower() else tool_name


def _append_audit(entry: dict[str, Any]) -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    rows: list[Any] = []
    if AUDIT_PATH.exists():
        try:
            loaded = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
            rows = loaded if isinstance(loaded, list) else [loaded]
        except json.JSONDecodeError:
            # Never silently drop history: park the unreadable file beside the new one.
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
            AUDIT_PATH.rename(AUDIT_PATH.with_name(f"audit_trail.corrupt-{stamp}.json"))
    rows.append(entry)
    AUDIT_PATH.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")


async def _run(message: str, deps: AgentDeps) -> AgentResult:
    result = await build_agent().run(message, deps=deps)
    reply = str(result.output)

    thoughts, native_calls = _inspect_messages(result.all_messages())
    for call in native_calls:
        call["tool"] = _normalise_native(call["tool"])

    calls = deps.calls + native_calls
    tools_used: list[str] = []
    for call in calls:
        if call["tool"] not in tools_used:
            tools_used.append(call["tool"])

    _append_audit(
        {
            "time": datetime.now(timezone.utc).isoformat(),
            "user_message": message,
            "thoughts": thoughts,
            "tool_calls": calls,
            "reply": reply,
            "stop_reason": "final_response",
        }
    )
    return AgentResult(reply=reply, tools_used=tools_used)


def run_agent(message: str) -> dict:
    """Run one turn of the course assistant. Always returns a reply, never raises."""
    deps = AgentDeps()
    try:
        return asyncio.run(_run(message, deps)).model_dump()
    except Exception as exc:
        _append_audit(
            {
                "time": datetime.now(timezone.utc).isoformat(),
                "user_message": message,
                "thoughts": [],
                "tool_calls": deps.calls,
                "reply": "",
                "stop_reason": f"error: {type(exc).__name__}: {exc}",
            }
        )
        return {
            "reply": f"Agent error: {exc}",
            "tools_used": [c["tool"] for c in deps.calls],
        }
