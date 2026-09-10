"""Shared Claude client for the model-backed agents.

One rule is enforced here rather than left to convention: nothing is sent to a
model until it has passed the invented-PII scan. The PII boundary is the model,
not the application -- legalapp.render may hold a client's name, a prompt may not.
"""
from __future__ import annotations

import functools

MODEL = "claude-opus-5"

#: Server-side refusal fallbacks: on a policy decline the API re-runs the same
#: request on a fallback model inside the same call, rather than simply stopping.
FALLBACK_BETAS = ["server-side-fallback-2026-07-01"]


class AgentUnavailable(RuntimeError):
    """No SDK or no credentials. Callers degrade instead of failing."""


class PIILeakBlocked(RuntimeError):
    """Refused to send text containing literal personal detail to a model."""


@functools.lru_cache(maxsize=1)
def get_client():
    try:
        import anthropic
    except ImportError as e:  # pragma: no cover - environment dependent
        raise AgentUnavailable(
            "the anthropic SDK is not installed -- pip install 'legalapp[agents]'"
        ) from e
    try:
        client = anthropic.Anthropic()
    except Exception as e:  # pragma: no cover - environment dependent
        raise AgentUnavailable(f"could not construct a Claude client: {e}") from e
    # The SDK constructs happily with no credential and only fails at request
    # time, so check here rather than discovering it mid-draft.
    if not (client.api_key or getattr(client, "auth_token", None)):
        raise AgentUnavailable(
            "no Claude credentials found. Set ANTHROPIC_API_KEY, or run `ant auth login`. "
            "The deterministic checks and the composer need no credential."
        )
    return client


def available() -> bool:
    try:
        get_client()
        return True
    except AgentUnavailable:
        return False


def assert_no_pii(text: str, what: str = "text") -> None:
    """Structural enforcement of the PII boundary. Raises rather than warns."""
    from .. import library
    from ..checks import pii

    leaks = pii.scan(text, what, extra_vocab=library.vocabulary())
    if leaks:
        found = ", ".join(sorted({f.excerpt for f in leaks}))
        raise PIILeakBlocked(
            f"refusing to send {what} to a model: it contains literal personal "
            f"detail ({found}). Replace it with declared placeholders first."
        )


def parse(*, system: str, prompt: str, output_format, effort: str = "high", max_tokens: int = 16000):
    """One structured call, with refusal handled rather than assumed away."""
    client = get_client()
    response = client.beta.messages.parse(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
        output_format=output_format,
        output_config={"effort": effort},
        thinking={"type": "adaptive"},
        betas=FALLBACK_BETAS,
        fallbacks="default",
    )
    if response.stop_reason == "refusal":
        detail = getattr(response.stop_details, "explanation", None) or "no explanation given"
        raise AgentUnavailable(f"the model declined this request ({detail})")
    return response.parsed_output
