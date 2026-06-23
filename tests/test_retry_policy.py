import pytest

from ofertas_bot.providers.retry import RetryPolicy


def test_retry_policy_retries_only_before_max_attempts() -> None:
    policy = RetryPolicy(max_attempts=3, retry_status_codes=(429,))

    assert policy.should_retry(status_code=429, attempt=1) is True
    assert policy.should_retry(status_code=429, attempt=2) is True
    assert policy.should_retry(status_code=429, attempt=3) is False
    assert policy.should_retry(status_code=200, attempt=1) is False


def test_retry_policy_calculates_backoff_delay() -> None:
    policy = RetryPolicy(
        max_attempts=3,
        base_delay_seconds=0.5,
        backoff_multiplier=2.0,
    )

    assert policy.delay_for_attempt(1) == 0.5
    assert policy.delay_for_attempt(2) == 1.0
    assert policy.delay_for_attempt(3) == 2.0


def test_retry_policy_rejects_invalid_config() -> None:
    with pytest.raises(ValueError, match="max_attempts"):
        RetryPolicy(max_attempts=0)

    with pytest.raises(ValueError, match="base_delay_seconds"):
        RetryPolicy(base_delay_seconds=-1)

    with pytest.raises(ValueError, match="backoff_multiplier"):
        RetryPolicy(backoff_multiplier=0.5)
