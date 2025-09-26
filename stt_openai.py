"""OpenAI Whisper transcription helper used by the FastAPI web UI.

This module provides a minimal wrapper around the OpenAI Speech-to-Text
API so other parts of the project can call a single ``transcribe_file``
function.  The original repository referenced ``stt_openai`` but the file
was missing, leading to ``ModuleNotFoundError`` at runtime.  The
implementation below intentionally keeps the public surface small while
handling the different OpenAI Python SDK versions that users might have
installed (``openai>=0.27`` as listed in ``requirements-web.txt`` covers
both the legacy ``openai`` module and the modern ``openai`` client).
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import openai

LOG = logging.getLogger(__name__)

# Default transcription model if none is provided in the configuration.
DEFAULT_MODEL = "whisper-1"


def _resolve_model(cfg: Optional[Dict[str, Any]] = None) -> str:
    """Return the Whisper model name from configuration or fallback."""

    if cfg and isinstance(cfg.get("stt"), dict):
        model = cfg["stt"].get("model")
        if isinstance(model, str) and model.strip():
            return model.strip()
    return DEFAULT_MODEL


def transcribe_file(
    file_path: str,
    *,
    language: Optional[str] = None,
    cfg: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> str:
    """Transcribe ``file_path`` with OpenAI Whisper and return the text.

    Parameters
    ----------
    file_path:
        Path to the audio file that should be transcribed.
    language:
        Optional BCP-47 language code hint (e.g. ``"sv"`` for Swedish).
    cfg:
        Optional project configuration dictionary.  When provided we look
        for ``cfg["stt"]["model"]`` to allow overrides of the model
        name.  Additional keyword arguments are forwarded to the OpenAI
        API call which makes the helper easy to extend without modifying
        this wrapper (for example ``temperature`` or ``prompt``).

    Returns
    -------
    str
        The transcribed text returned by the OpenAI API.

    Raises
    ------
    FileNotFoundError
        If the supplied ``file_path`` does not exist.
    RuntimeError
        If the OpenAI API call fails or the response cannot be parsed.
    """

    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    model = _resolve_model(cfg)
    params: Dict[str, Any] = {"model": model}
    if language:
        params["language"] = language
    params.update(kwargs)

    # The OpenAI Python SDK introduced a new client interface in v1.0.0.
    # We support both the classic module-level functions (openai<1.0) and
    # the newer ``OpenAI`` client to maximise compatibility for users
    # following older documentation.
    try:
        from openai import OpenAI  # type: ignore
    except ImportError:  # pragma: no cover - legacy SDK path
        OpenAI = None  # type: ignore

    try:
        if OpenAI is not None and hasattr(openai, "OpenAI"):
            client = OpenAI(api_key=getattr(openai, "api_key", None) or None)
            with open(file_path, "rb") as fh:
                response = client.audio.transcriptions.create(file=fh, **params)
            # The new client returns a pydantic model with a ``text`` attribute.
            text = getattr(response, "text", None)
            if text:
                return str(text)
            raise RuntimeError("OpenAI transcription response missing text")

        # Fallback to legacy interface (openai<1.0 style).
        with open(file_path, "rb") as fh:
            response = openai.Audio.transcribe(file=fh, **params)  # type: ignore[attr-defined]
        if isinstance(response, dict) and "text" in response:
            return str(response["text"])
        if hasattr(response, "get"):
            text = response.get("text")  # type: ignore[assignment]
            if text is not None:
                return str(text)
        raise RuntimeError("OpenAI transcription response missing text field")
    except Exception as exc:  # pragma: no cover - requires network/API
        LOG.exception("OpenAI transcription failed")
        raise RuntimeError(f"OpenAI transcription failed: {exc}") from exc


__all__ = ["transcribe_file"]
