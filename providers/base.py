from __future__ import annotations

from typing import Protocol

from schemas import ProviderRequest, ProviderResponse


class AnalysisProvider(Protocol):
    provider_name: str

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        """Execute one qualitative-analysis provider call."""
