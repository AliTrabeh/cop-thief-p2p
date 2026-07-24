"""The Gatekeeper's rate-limiter config shape, split out of ``game_config.py``
to keep that file under 150 lines — a standalone concern used by both
:class:`~police_thief.domain.game_config.GameConfig` and
``infra/gatekeeper.py`` directly.
"""

from __future__ import annotations

from pydantic import Field

from police_thief.domain.models import _StrictConfigModel


class RateLimiterGatekeeperConfig(_StrictConfigModel):
    requests_per_minute: int = Field(ge=30, default=30)
    concurrent_requests: int = Field(ge=2, default=2)
    retry_backoff_sec: int = Field(ge=5, default=5)
    max_retries: int = Field(ge=3, default=3)
    queue_depth: int = Field(ge=100, default=100)
