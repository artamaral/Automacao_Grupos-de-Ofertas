from __future__ import annotations

from dataclasses import dataclass
from time import sleep as system_sleep
from typing import Protocol


class Sleeper(Protocol):
    def sleep(self, seconds: float) -> None:
        """Wait before the next retry attempt."""


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: float = 0.5
    backoff_multiplier: float = 2.0
    retry_status_codes: tuple[int, ...] = (429, 500, 502, 503, 504)

    def __post_init__(self) -> None:
        if self.max_attempts <= 0:
            msg = "Retry max_attempts must be greater than zero"
            raise ValueError(msg)
        if self.base_delay_seconds < 0:
            msg = "Retry base_delay_seconds must not be negative"
            raise ValueError(msg)
        if self.backoff_multiplier < 1:
            msg = "Retry backoff_multiplier must be greater than or equal to 1"
            raise ValueError(msg)

    def should_retry(self, status_code: int, attempt: int) -> bool:
        return attempt < self.max_attempts and status_code in self.retry_status_codes

    def delay_for_attempt(self, attempt: int) -> float:
        return self.base_delay_seconds * (self.backoff_multiplier ** (attempt - 1))


class NoOpSleeper:
    def sleep(self, seconds: float) -> None:
        return None


class SystemSleeper:
    def sleep(self, seconds: float) -> None:
        system_sleep(seconds)
