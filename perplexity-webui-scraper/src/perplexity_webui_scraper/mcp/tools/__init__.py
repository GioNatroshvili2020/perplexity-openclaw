"""Register model-specific query tools on a FastMCP instance."""

from __future__ import annotations

import os
from collections.abc import Callable  # noqa: TC003
from typing import Any

from perplexity_webui_scraper._internal.exceptions import ModelStatusError
from perplexity_webui_scraper._internal.types import SearchFocus, SourceFocus, TimeRange  # noqa: TC001
from perplexity_webui_scraper.core.client import Perplexity  # noqa: TC001
from perplexity_webui_scraper.mcp.tools.ask import _ask, session_status
from perplexity_webui_scraper.models.registry import MODELS
from perplexity_webui_scraper.models.types import Model, ModelMode  # noqa: TC001


def _wanted_models() -> list[Model]:
    """Return the models to expose, filtered by ``PERPLEXITY_MODELS``.

    ``PERPLEXITY_MODELS`` is a comma-separated list of model ids or tool names
    (e.g. ``best,gpt56_terra,kimi_k3_thinking,claude_s50``). When unset, every
    registered model is exposed. Reducing this list is the biggest token saver.
    """
    spec = os.environ.get("PERPLEXITY_MODELS", "").strip()

    if not spec:
        return MODELS.list_all()

    wanted = {token.strip() for token in spec.split(",") if token.strip()}

    def matches(model: Model) -> bool:
        short = model.tool_name.removeprefix("pplx_")
        id_tail = model.id.rsplit("/", 1)[1] if "/" in model.id else model.id

        return model.id in wanted or model.tool_name in wanted or short in wanted or id_tail in wanted

    return [model for model in MODELS.list_all() if matches(model)]


def register_all_tools(mcp: Any, get_client: Callable[[], Perplexity]) -> None:
    """Register one MCP tool per model onto *mcp*.

    Each tool is named ``{model.tool_name}`` and delegates to :func:`_ask`
    with the corresponding :class:`~perplexity_webui_scraper.models.types.Model`
    pre-bound. The ``pplx_custom`` and ``pplx_session_status`` tools are always
    registered.

    Args:
        mcp: The :class:`fastmcp.FastMCP` server instance.
        get_client: Zero-argument callable returning the active
            :class:`~perplexity_webui_scraper.Perplexity` client.
    """
    for model in _wanted_models():
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
        files: list[str] | None = None,
        output_path: str | None = None,
        strip_fence: bool = True,
        include_search_results: bool = False,
        max_chars: int | None = None,
        search_focus: SearchFocus = "web",
        source_focus: SourceFocus = "web",
        time_range: TimeRange = "all",
        language: str = "en-US",
        latitude: float | None = None,
        longitude: float | None = None,
        allow_risky_model: bool = False,
        research_interaction: str = "auto",
    ) -> dict[str, Any]:
        """Ask Perplexity and return a cleaned answer.

        Reuses this model's ongoing conversation by default (same chat). Set
        ``new_chat=True`` for a one-off task. The answer has ``[url](url)``
        artifacts reverted and, by default, one wrapping code fence stripped.

        Args:
            query: The question or prompt.
            new_chat: Start a fresh conversation instead of continuing this model's thread.
            thread_uuid: Continue a specific thread by its UUID.
            files: Optional local file paths to upload as attachments (avoids pasting their contents).
            output_path: Optional file path to write the answer to; returns a short preview instead of the full text.
            strip_fence: Remove one wrapping markdown code fence from the answer.
            include_search_results: Also return the ``search_results`` list.
            max_chars: Truncate the answer to this many characters.
            search_focus: ``"web"`` (search) or ``"writing"`` (no sources; forced when files are attached).
            source_focus: ``"web"``, ``"academic"``, ``"social"``, ``"finance"``, or ``"all"``.
            time_range: ``"all"``, ``"day"``, ``"week"``, ``"month"``, or ``"year"``.
            language: BCP-47 tag, e.g. ``"en-US"``.
            latitude: Optional latitude for location-aware results.
            longitude: Optional longitude for location-aware results.
            allow_risky_model: Acknowledge a non-available model status.
            research_interaction: ``"auto"`` or ``"manual"``.

        Returns:
            Dict with ``answer`` (or ``file`` + ``preview``) and ``conversation_uuid``.
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
            files=files,
            output_path=output_path,
            strip_fence=strip_fence,
            include_search_results=include_search_results,
            max_chars=max_chars,
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
        files: list[str] | None = None,
        output_path: str | None = None,
        strip_fence: bool = True,
        include_search_results: bool = False,
        max_chars: int | None = None,
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
            files=files,
            output_path=output_path,
            strip_fence=strip_fence,
            include_search_results=include_search_results,
            max_chars=max_chars,
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
