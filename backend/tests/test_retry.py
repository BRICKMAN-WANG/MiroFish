"""Tests for retry utilities."""

import time
import asyncio
import pytest

from app.utils.retry import (
    retry_with_backoff,
    retry_with_backoff_async,
    RetryableAPIClient,
)


class TestRetryWithBackoff:
    def test_success_on_first_try(self):
        """Should succeed immediately without retries."""
        call_count = 0

        @retry_with_backoff(max_retries=3)
        def func():
            nonlocal call_count
            call_count += 1
            return "ok"

        assert func() == "ok"
        assert call_count == 1

    def test_retry_then_succeed(self):
        """Should retry twice then succeed on the third attempt."""
        call_count = 0

        @retry_with_backoff(max_retries=3, initial_delay=0.01)
        def func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("not yet")
            return "success"

        assert func() == "success"
        assert call_count == 3

    def test_exhaust_retries(self):
        """Should raise after exhausting all retries."""
        call_count = 0

        @retry_with_backoff(max_retries=2, initial_delay=0.01)
        def func():
            nonlocal call_count
            call_count += 1
            raise ValueError("always fails")

        with pytest.raises(ValueError, match="always fails"):
            func()
        assert call_count == 3  # 1 original + 2 retries

    def test_on_retry_callback(self):
        """on_retry callback should be invoked on each retry."""
        call_count = 0
        retry_log = []

        def on_retry(exc, attempt):
            retry_log.append((exc, attempt))

        @retry_with_backoff(max_retries=2, initial_delay=0.01, on_retry=on_retry)
        def func():
            nonlocal call_count
            call_count += 1
            raise ValueError("fail")

        with pytest.raises(ValueError):
            func()
        assert len(retry_log) == 2
        assert isinstance(retry_log[0][0], ValueError)
        assert retry_log[0][1] == 1

    def test_specific_exception_only(self):
        """Should only retry on specified exception types."""

        @retry_with_backoff(
            max_retries=2, initial_delay=0.01, exceptions=(ValueError,)
        )
        def func():
            raise TypeError("wrong type")

        with pytest.raises(TypeError):
            func()

    def test_jitter_disabled(self):
        """Should be reproducible without jitter."""
        call_count = 0

        @retry_with_backoff(max_retries=2, initial_delay=0.01, jitter=False)
        def func():
            nonlocal call_count
            call_count += 1
            raise ValueError("fail")

        t0 = time.perf_counter()
        with pytest.raises(ValueError):
            func()
        elapsed = time.perf_counter() - t0
        # 1st retry: 0.01s, 2nd: 0.02s
        assert call_count == 3


class TestRetryWithBackoffAsync:
    @pytest.mark.asyncio
    async def test_async_success_first_try(self):
        call_count = 0

        @retry_with_backoff_async(max_retries=2)
        async def func():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await func()
        assert result == "ok"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_async_retry_then_succeed(self):
        call_count = 0

        @retry_with_backoff_async(max_retries=3, initial_delay=0.01)
        async def func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("timeout")
            return "recovered"

        result = await func()
        assert result == "recovered"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_async_exhaust_retries(self):
        call_count = 0

        @retry_with_backoff_async(max_retries=1, initial_delay=0.01)
        async def func():
            nonlocal call_count
            call_count += 1
            raise RuntimeError("persistent")

        with pytest.raises(RuntimeError, match="persistent"):
            await func()
        assert call_count == 2


class TestRetryableAPIClient:
    def test_call_with_retry_success(self):
        client = RetryableAPIClient(max_retries=2, initial_delay=0.01)
        assert client.call_with_retry(lambda: 42) == 42

    def test_call_with_retry_failure(self):
        client = RetryableAPIClient(max_retries=1, initial_delay=0.01)

        def fail():
            raise ValueError("nope")

        with pytest.raises(ValueError, match="nope"):
            client.call_with_retry(fail)

    def test_call_with_retry_custom_exception(self):
        client = RetryableAPIClient(max_retries=2, initial_delay=0.01)
        call_count = 0

        def func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise KeyError("missing")
            return "found"

        result = client.call_with_retry(func, exceptions=(KeyError,))
        assert result == "found"
        assert call_count == 2

    def test_call_batch_with_retry_all_succeed(self):
        client = RetryableAPIClient(max_retries=1, initial_delay=0.01)
        results, failures = client.call_batch_with_retry(
            [1, 2, 3], lambda x: x * 2
        )
        assert results == [2, 4, 6]
        assert failures == []

    def test_call_batch_with_retry_some_fail(self):
        client = RetryableAPIClient(max_retries=1, initial_delay=0.01)

        def process(x):
            if x == 2:
                raise ValueError("bad")
            return x * 10

        results, failures = client.call_batch_with_retry(
            [1, 2, 3], process, continue_on_failure=True
        )
        assert results == [10, 30]
        assert len(failures) == 1
        assert failures[0]["index"] == 1

    def test_call_batch_with_retry_stop_on_failure(self):
        client = RetryableAPIClient(max_retries=1, initial_delay=0.01)

        def process(x):
            if x == 2:
                raise ValueError("bad")
            return x

        with pytest.raises(ValueError, match="bad"):
            client.call_batch_with_retry(
                [1, 2, 3], process, continue_on_failure=False
            )
