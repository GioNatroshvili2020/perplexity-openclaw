"""Register model-specific query tools on a FastMCP instance."""

from __future__ import annotations

from collections.abc import Callable  # noqa: TC003
from typing import Any

from perplexity_webui_scraper._internal.exceptions import ModelStatusError
from perplexity_webui_scraper._internal.types import SearchFocus, SourceFocus, TimeRange  # noqa: TC001
from perplexity_webui_scraper.core.client import Perplexity  # noqa: TC001
from perplexity_webui_scraper.mcp.tools.ask import _ask, session_status
from perplexity_webui_scraper.models.registry import MODELS
from perplexity_webui_scraper.models.types import ModelMode  # noqa: TC001


def register_all_tools(mcp: Any, get_client: Callable[[], Perplexity]) -> None:
    """Register one MCP tool per model onto *mcp*.

    Each tool is named ``{model.tool_name}`` and delegates to :func:`_ask`
    with the corresponding :class:`~perplexity_webui_scraper.models.types.Model`
    pre-bound.

    Args:
        mcp: The :class:`fastmcp.FastMCP` server instance.
        get_client: Zero-argument callable returning the active
            :class:`~perplexity_webui_scraper.Perplexity` client.
    """
    for model in MODELS.list_all():
        description = f"[{model.status.upper()}] [{model.name}] {model.description}"
        _register_model_tool(mcp, model.tool_name, model.id, description, get_client)

    _register_custom_tool(mcp, get_client)
    _register_session_status_tool(mcp, get_client)


def _register_model_tool(
    mcp: Any,
    tool_name: str,
    model_id: str,
    model_description: str,
    get_client: Callable[[], Perplexity],
) -> None:
    """Register a single model tool onto the MCP server.

    Args:
        mcp: FastMCP instance.
        tool_name: The tool name (snake_case).
        model_id: Canonical model ID for client lookup.
        model_description: Short model description for the tool description.
        get_client: Callable returning the active Perplexity client.
    """
    resolved_model = MODELS.resolve(model_id)

    @mcp.tool(name=tool_name, description=model_description)
    def _tool(
        query: str,
        new_chat: bool = False,
        thread_uuid: str | None = None,
        search_focus: SearchFocus = "web",
        source_focus: SourceFocus = "web",
        time_range: TimeRange = "all",
        language: str = "en-US",
        latitude: float | None = None,
        longitude: float | None = None,
        allow_risky_model: bool = False,
        research_interaction: str = "auto",
    ) -> dict[str, Any]:
        """Search Perplexity AI and return the answer with citations.

        Reuses this model's ongoing conversation by default (same chat). Set
        ``new_chat=True`` for a single-use task that should start fresh.

        Args:
            query: The search query or question.
            new_chat: When ``True``, start a fresh conversation instead of reusing
                this model's current thread. Default ``False`` (continue same chat).
            thread_uuid: Optional UUID of a specific thread to continue.
            search_focus: ``"web"`` (default) or ``"writing"`` (no sources).
            source_focus: Source filter: ``"web"``, ``"academic"``,
                ``"social"``, ``"finance"``, or ``"all"``.
            time_range: Recency filter: ``"all"``, ``"day"``, ``"week"``,
                ``"month"``, or ``"year"``.
            language: BCP-47 response language tag (e.g. ``"en-US"``).
            latitude: Optional latitude for location-aware results.
            longitude: Optional longitude for location-aware results.
            allow_risky_model: Acknowledge any non-available model status.
            research_interaction: Deep Research clarification handling: ``"auto"`` or ``"manual"``.

        Returns:
            Dict with ``answer``, ``search_results``, and ``conversation_uuid``.
        """
        return _ask(
            client=get_client(),
            model=resolved_model,
            query=query,
            search_focus=search_focus,
            source_focus=source_focus,
            time_range=time_range,
            language=language,
            latitude=latitude,
            longitude=longitude,
            allow_risky_model=allow_risky_model,
            research_interaction=research_interaction,
            thread_uuid=thread_uuid,
            new_chat=new_chat,
        )


def _register_custom_tool(mcp: Any, get_client: Callable[[], Perplexity]) -> None:
    """Register the generic tool for arbitrary Perplexity internal identifiers."""

    @mcp.tool(
        name="pplx_custom",
        description=(
            "[UNKNOWN] Query an unregistered Perplexity internal model identifier. "
            "Its current availability has not been confirmed."
        ),
    )
    def _custom_tool(
        model: str,
        query: str,
        new_chat: bool = False,
        thread_uuid: str | None = None,
        model_mode: ModelMode = "copilot",
        search_focus: SearchFocus = "web",
        source_focus: SourceFocus = "web",
        time_range: TimeRange = "all",
        language: str = "en-US",
        latitude: float | None = None,
        longitude: float | None = None,
        allow_risky_model: bool = False,
        research_interaction: str = "auto",
    ) -> dict[str, Any]:
        """Query a custom internal identifier after explicit risk acknowledgement."""
        model_id = model if model.startswith("custom:") else f"custom:{model}"

        try:
            resolved = MODELS.resolve_for_use(
                model_id,
                allow_risky_model=allow_risky_model,
                custom_model_mode=model_mode,
            )
        except (ValueError, ModelStatusError) as exc:
            return {"error": str(exc), "error_type": "custom_model_invalid", "model": model_id}

        return _ask(
            client=get_client(),
            model=resolved,
            query=query,
            search_focus=search_focus,
            source_focus=source_focus,
            time_range=time_range,
            language=language,
            latitude=latitude,
            longitude=longitude,
            allow_risky_model=allow_risky_model,
            research_interaction=research_interaction,
            thread_uuid=thread_uuid,
            new_chat=new_chat,
        )


def _register_session_status_tool(mcp: Any, get_client: Callable[[], Perplexity]) -> None:
    """Register a tool that reports the Perplexity session cookie status."""

    @mcp.tool(
        name="pplx_session_status",
        description=(
            "Check the Perplexity session cookie status. Returns whether it is valid, "
            "the account tier, email, and expiry timestamp. Use this to detect when the "
            "cookie has expired so the user can reshare a new one."
        ),
    )
    def _session_status() -> dict[str, Any]:
        """Report the Perplexity session cookie validity and expiry."""
        return session_status(get_client())
