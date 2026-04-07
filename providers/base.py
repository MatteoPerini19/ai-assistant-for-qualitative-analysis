from __future__ import annotations

from typing import Protocol

from schemas import ProviderRequest, ProviderResponse


class AnalysisProvider(Protocol):
    provider_name: str

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        """Execute one qualitative-analysis provider call.

        Providers return a `ProviderResponse` for both successful calls and
        provider-side failures. Once request metadata is available, failures should
        stay in-band as `parse_status='provider_error'` responses so downstream
        stages can preserve one auditable long-output record shape per attempted
        call.
        """
