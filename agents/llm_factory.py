"""Deterministic local query responder used by the audit subsystem."""

from .base import PHIGuard


class MockLLM:
    """A deterministic local responder; no external model or network call is made."""

    def __init__(self, system_name: str = "CRISPR Off-Target Agent"):
        self.system_name = system_name

    def invoke(self, prompt: str) -> str:
        PHIGuard.assert_no_phi(prompt)
        preview = str(prompt).strip().replace("\n", " ")[:120]
        return (
            f"[{self.system_name} deterministic mode] Query accepted: {preview!r}. "
            "No external language model was called."
        )


class LLMFactory:
    """Create the only inference provider implemented by this repository."""

    @staticmethod
    def create(provider: str = "mock", system_name: str = "CRISPR Off-Target Agent"):
        normalized = str(provider).strip().lower()
        if normalized in {"mock", "deterministic", "test"}:
            return MockLLM(system_name)
        raise ValueError(
            f"Unsupported model provider {provider!r}. "
            "This repository currently implements deterministic local mode only."
        )
