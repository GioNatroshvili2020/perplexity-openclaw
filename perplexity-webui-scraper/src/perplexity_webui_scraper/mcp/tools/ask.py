"""Shared ask logic and dynamic tool factory for MCP tools."""

from __future__ import annotations

import re
from time import time
from typing import TYPE_CHECKING, Any, cast

from perplexity_webui_scraper._internal.exceptions import (
    AuthenticationError,
    FileAccessError,
    ModelAccessError,
    ModelStatusError,
    RateLimitError,
)
from perplexity_webui_scraper.config.conversation import ConversationConfig
from perplexity_webui_scraper.core.response import Coordinates


if TYPE_CHECKING:
    from perplexity_webui_scraper._internal.types import (
        ResearchInteraction,
        SearchFocus,
        SourceFocus,
        TimeRange,
    )
    from perplexity_webui_scraper.core.client import Perplexity
    from perplexity_webui_scraper.core.conversation import Conversation
    from perplexity_webui_scraper.models.types import Model


SESSION_EXPIRED_MESSAGE: str = (
    "Your Perplexity session cookie has expired or is invalid. Sign in again at "
    "perplexity.ai, copy the '__Secure-pplx.session.<id>' (or '__Secure-next-auth.session-token') "
    "cookie value, update PERPLEXITY_SESSION_TOKEN in OpenClaw, and reshare the new cookie."
)

_CONVERSATION_TTL_SECONDS: float = 30 * 60
"""Idle timeout for cached conversations (matches the HTTP API)."""

_DEFAULT_THREADS: dict[str, tuple[Conversation, float]] = {}
"""Per-model persistent conversation, reused by default (keyed by model id)."""

_THREADS_BY_UUID: dict[str, tuple[Conversation, float]] = {}
"""Conversation cache keyed by Perplexity thread UUID for explicit continuation."""

# Perplexity auto-linkifies bare URLs into markdown ``[url](url)``; revert it.
_LINK_ARTIFACT_RE = re.compile(r"\[([^\]\n]*)\]\((https?://[^)\s]+)\)")

# A single wrapping markdown code fence (```html ... ```) around the whole answer.
_FENCE_RE = re.compile(r"^\s*`{3,}[a-zA-Z0-9_+-]*\s*\n(.*?)\n?`{3,}\s*$", re.DOTALL)


def _delinkify(text: str) -> str:
    """Rewrite Perplexity's injected ``[label](url)`` back to the bare URL."""
    return _LINK_ARTIFACT_RE.sub(lambda m: m.group(2), text)


def _strip_fence(text: str) -> str:
    """Remove one wrapping markdown code fence when the whole answer is fenced."""
    match = _FENCE_RE.match(text.strip())
    return match.group(1) if match else text


def _truncate(text: str, max_chars: int | None) -> str:
    """Truncate *text* to *max_chars* with an explicit marker (no silent cutoff)."""
    if max_chars and len(text) > max_chars:
        return text[:max_chars] + "\n... [truncated]"
    return text


def _evict_stale() -> None:
    """Drop conversations that have been idle past the TTL."""
    now = time()

    for store in (_DEFAULT_THREADS, _THREADS_BY_UUID):
        stale = [key for key, (_conversation, ts) in store.items() if now - ts > _CONVERSATION_TTL_SECONDS]

        for key in stale:
            del store[key]


def _get_thread(store: dict[str, tuple[Conversation, float]], key: str) -> Conversation | None:
    """Return a cached conversation for *key*, refreshing its last-access time."""
    _evict_stale()
    entry = store.get(key)

    if entry is None:
        return None

    conversation, _ts = entry
    store[key] = (conversation, time())

    return conversation


def _cache_thread(conversation: Conversation) -> None:
    """Record *conversation* in the UUID-keyed cache for explicit continuation."""
    if conversation.uuid:
        _evict_stale()
        _THREADS_BY_UUID[conversation.uuid] = (conversation, time())


def _session_expired() -> dict[str, Any]:
    """Return the standard expired-session error payload."""
    return {"error": SESSION_EXPIRED_MESSAGE, "error_type": "session_expired"}


def session_status(client: Perplexity) -> dict[str, Any]:
    """Return the Perplexity session status for the configured cookie.

    Args:
        client: Active :class:`~perplexity_webui_scraper.Perplexity` client.

    Returns:
        Dict with ``valid`` (bool), ``account_tier``, ``email``, and ``expires``.
        When invalid, ``valid`` is ``False`` and an ``error`` string is included.
    """
    try:
        session = client.get_account_session()
    except AuthenticationError:
        return {"valid": False, "account_tier": None, "email": None, "expires": None, "error": SESSION_EXPIRED_MESSAGE}
    except Exception as exc:  # noqa: BLE001
        return {"valid": False, "account_tier": None, "email": None, "expires": None, "error": str(exc)}

    user = session.user

    return {
        "valid": user is not None,
        "account_tier": session.account_tier,
        "email": user.email if user is not None else None,
        "expires": session.expires,
    }


def _ask(
    client: Perplexity,
    model: Model,
    query: str,
    search_focus: SearchFocus = "web",
    source_focus: SourceFocus = "web",
    time_range: TimeRange = "all",
    language: str = "en-US",
    latitude: float | None = None,
    longitude: float | None = None,
    allow_risky_model: bool = False,
    research_interaction: str = "auto",
    thread_uuid: str | None = None,
    new_chat: bool = False,
    strip_fence: bool = True,
    include_search_results: bool = False,
    max_chars: int | None = None,
) -> dict[str, Any]:
    """Execute a single Perplexity query and return a structured result dict.

    By default the query is sent as a follow-up to this model's persistent
    conversation (same chat). Set ``new_chat=True`` to start a fresh chat for a
    single-use task. Pass ``thread_uuid`` to continue a specific thread.

    The answer is cleaned for direct use: injected ``[url](url)`` artifacts are
    reverted to bare URLs and, unless ``strip_fence=False``, a single wrapping
    markdown code fence is removed. ``max_chars`` truncates with an explicit
    marker. ``include_search_results`` opts into shipping web citations.

    Args:
        client: Active :class:`~perplexity_webui_scraper.Perplexity` client.
        model: The resolved :class:`~perplexity_webui_scraper.models.types.Model`.
        query: The user's search query.
        search_focus: ``"web"`` for web search; ``"writing"`` for pure generation.
        source_focus: Source category filter.
        time_range: Recency filter for search results.
        language: BCP-47 response language tag.
        latitude: Optional latitude for localised results.
        longitude: Optional longitude for localised results.
        allow_risky_model: Acknowledge any non-available model status.
        research_interaction: Deep Research clarification handling: ``"auto"`` or ``"manual"``.
        thread_uuid: Optional UUID of a specific thread to continue (overrides the default).
        new_chat: When ``True``, start a fresh conversation instead of reusing this
            model's current thread.
        strip_fence: Remove a single wrapping markdown code fence from the answer.
        include_search_results: Include the ``search_results`` list in the result.
        max_chars: Truncate the answer to this many characters (with a marker).

    Returns:
        Dict with ``answer``, and optionally ``search_results`` and ``conversation_uuid``.
    """
    # 1. Proactive session check so an expired cookie is reported immediately.
    if not session_status(client).get("valid"):
        return _session_expired()

    # 2. Resolve which conversation to use.
    conversation: Conversation | None = None
    explicit_thread = False

    if thread_uuid:
        explicit_thread = True
        conversation = _get_thread(_THREADS_BY_UUID, thread_uuid)

        if conversation is None:
            return {
                "error": f"Conversation '{thread_uuid}' not found or expired. Start fresh with new_chat=true.",
                "error_type": "thread_not_found",
            }
    elif not new_chat:
        conversation = _get_thread(_DEFAULT_THREADS, model.id)

    if conversation is None:
        coordinates: Coordinates | None = None

        if latitude is not None and longitude is not None:
            coordinates = Coordinates(latitude=latitude, longitude=longitude)

        config = ConversationConfig(
            model=model.id,
            search_focus=search_focus,
            source_focus=source_focus,
            time_range=time_range,
            citation_mode="clean",
            language=language,
            coordinates=coordinates,
            allow_risky_model=allow_risky_model,
            custom_model_mode=model.mode,
            research_interaction=cast("ResearchInteraction", research_interaction),
        )

        conversation = client.create_conversation(config)

    # 3. Ask.
    try:
        conversation.ask(query)
    except AuthenticationError:
        return _session_expired()
    except RateLimitError as exc:
        return {"error": str(exc), "error_type": "rate_limited"}
    except ModelAccessError as exc:
        return {
            "error": str(exc),
            "error_type": "model_access_denied",
            "model": exc.model_id,
            "required_tier": exc.required_tier,
            "account_tier": exc.account_tier,
        }
    except FileAccessError as exc:
        return {
            "error": str(exc),
            "error_type": "file_access_denied",
            "account_tier": exc.account_tier,
        }
    except ModelStatusError as exc:
        return {
            "error": str(exc),
            "error_type": "model_status_confirmation_required",
            "model": exc.model_id,
            "status": exc.status,
        }

    # 4. Clean the answer for direct use.
    answer = _delinkify(conversation.answer or "")
    if strip_fence:
        answer = _strip_fence(answer)
    answer = _truncate(answer, max_chars)

    # 5. Cache. The default thread only advances on the default flow (not when
    #    an explicit thread_uuid was continued).
    _cache_thread(conversation)

    if not explicit_thread:
        _DEFAULT_THREADS[model.id] = (conversation, time())

    result: dict[str, Any] = {"answer": answer}

    if include_search_results and conversation.search_results:
        result["search_results"] = [
            {"title": r.title, "url": r.url, "snippet": r.snippet} for r in conversation.search_results
        ]

    if conversation.uuid:
        result["conversation_uuid"] = conversation.uuid

    return result
