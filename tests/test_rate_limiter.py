import asyncio
import time

from utils.rate_limiter import RateLimiter


async def test_rate_limiter_allows_within_limit() -> None:
    """Test that requests within limit are allowed."""
    limiter = RateLimiter(max_requests=5, window_seconds=60, cooldown_seconds=30)

    for i in range(5):
        is_limited, remaining = await limiter.is_rate_limited(123)
        assert not is_limited, f"Request {i+1} should be allowed"


async def test_rate_limiter_blocks_after_limit() -> None:
    """Test that requests exceeding limit are blocked."""
    limiter = RateLimiter(max_requests=3, window_seconds=60, cooldown_seconds=30)

    # Make 3 requests (should all pass)
    for i in range(3):
        is_limited, _ = await limiter.is_rate_limited(456)
        assert not is_limited

    # 4th request should be blocked
    is_limited, remaining = await limiter.is_rate_limited(456)
    assert is_limited
    assert remaining > 0
    assert remaining <= 30


async def test_rate_limiter_resets_after_cooldown() -> None:
    """Test that rate limit resets after cooldown period."""
    limiter = RateLimiter(max_requests=2, window_seconds=1, cooldown_seconds=1)

    # Exhaust limit
    await limiter.is_rate_limited(789)
    await limiter.is_rate_limited(789)
    is_limited, _ = await limiter.is_rate_limited(789)
    assert is_limited

    # Wait for cooldown + window to expire
    await asyncio.sleep(2.1)

    # Should be allowed again
    is_limited, remaining = await limiter.is_rate_limited(789)
    assert not is_limited


async def test_rate_limiter_per_user_isolation() -> None:
    """Test that rate limits are isolated per user."""
    limiter = RateLimiter(max_requests=2, window_seconds=60, cooldown_seconds=30)

    # Exhaust limit for user 1
    await limiter.is_rate_limited(111)
    await limiter.is_rate_limited(111)
    is_limited, _ = await limiter.is_rate_limited(111)
    assert is_limited

    # User 2 should still be allowed
    is_limited, _ = await limiter.is_rate_limited(222)
    assert not is_limited


async def test_rate_limiter_reset() -> None:
    """Test that reset clears rate limit for a user."""
    limiter = RateLimiter(max_requests=2, window_seconds=60, cooldown_seconds=30)

    # Exhaust limit
    await limiter.is_rate_limited(333)
    await limiter.is_rate_limited(333)
    is_limited, _ = await limiter.is_rate_limited(333)
    assert is_limited

    # Reset
    await limiter.reset(333)

    # Should be allowed again
    is_limited, _ = await limiter.is_rate_limited(333)
    assert not is_limited
