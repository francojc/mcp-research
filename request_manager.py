"""Request management system with deduplication and exponential backoff."""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class PendingRequest:
    """Represents a pending request with deduplication support."""
    future: asyncio.Future
    started_at: datetime = field(default_factory=datetime.now)
    request_count: int = 1


@dataclass
class RetryConfig:
    """Configuration for exponential backoff retry logic."""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True


class RequestManager:
    """Manages requests with deduplication and retry logic."""

    def __init__(self):
        self._pending_requests: Dict[str, PendingRequest] = {}
        self._retry_counts: Dict[str, int] = {}
        self._last_request_time: Dict[str, float] = {}
        self._lock = asyncio.Lock()

    def _generate_request_key(self, endpoint: str, **kwargs) -> str:
        """Generate a unique key for request deduplication."""
        key_parts = [endpoint]
        for key, value in sorted(kwargs.items()):
            key_parts.append(f"{key}={value}")
        return "|".join(key_parts)

    async def _calculate_backoff_delay(
        self,
        attempt: int,
        config: RetryConfig,
        error: Optional[Exception] = None
    ) -> float:
        """Calculate exponential backoff delay."""
        if attempt == 0:
            return 0

        # Calculate base delay with exponential backoff
        delay = min(
            config.base_delay * (config.exponential_base ** (attempt - 1)),
            config.max_delay
        )

        # Add jitter to prevent thundering herd
        if config.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)

        # Special handling for rate limit errors (429)
        if error and hasattr(error, 'response') and hasattr(error.response, 'status_code'):
            if error.response.status_code == 429:
                # For rate limits, use longer delays
                delay = max(delay, 30.0)

                # Check for Retry-After header
                retry_after = error.response.headers.get('Retry-After')
                if retry_after:
                    try:
                        delay = max(delay, float(retry_after))
                    except ValueError:
                        pass

        logger.debug(f"Calculated backoff delay: {delay:.2f}s for attempt {attempt}")
        return delay

    async def deduplicated_request(
        self,
        request_func: Callable[..., Awaitable[Any]],
        endpoint: str,
        retry_config: Optional[RetryConfig] = None,
        min_interval: float = 0.1,
        **request_kwargs
    ) -> Any:
        """
        Execute a request with deduplication and retry logic.

        Args:
            request_func: The async function to execute
            endpoint: Unique endpoint identifier for deduplication
            retry_config: Retry configuration (uses defaults if None)
            min_interval: Minimum interval between requests to same endpoint
            **request_kwargs: Arguments to pass to request_func
        """
        if retry_config is None:
            retry_config = RetryConfig()

        request_key = self._generate_request_key(endpoint, **request_kwargs)

        async with self._lock:
            # Check if there's already a pending request for the same parameters
            if request_key in self._pending_requests:
                pending = self._pending_requests[request_key]
                pending.request_count += 1
                logger.debug(f"Deduplicating request: {request_key} (count: {pending.request_count})")

                # Wait for the existing request to complete
                try:
                    result = await pending.future
                    logger.debug(f"Deduplicated request completed: {request_key}")
                    return result
                except Exception as e:
                    logger.debug(f"Deduplicated request failed: {request_key} - {e}")
                    raise

            # Check minimum interval between requests to same endpoint
            last_time = self._last_request_time.get(endpoint, 0)
            elapsed = time.time() - last_time
            if elapsed < min_interval:
                wait_time = min_interval - elapsed
                logger.debug(f"Rate limiting endpoint {endpoint}: waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)

            # Create new request
            future = asyncio.Future()
            self._pending_requests[request_key] = PendingRequest(future=future)

        # Execute request with retry logic
        attempt = 0
        last_error = None

        while attempt <= retry_config.max_retries:
            try:
                if attempt > 0:
                    delay = await self._calculate_backoff_delay(attempt, retry_config, last_error)
                    if delay > 0:
                        logger.info(f"Retrying request {request_key} after {delay:.2f}s (attempt {attempt})")
                        await asyncio.sleep(delay)

                # Update last request time
                self._last_request_time[endpoint] = time.time()

                # Execute the actual request
                logger.debug(f"Executing request: {request_key} (attempt {attempt + 1})")
                result = await request_func(**request_kwargs)

                # Success - clean up and return
                async with self._lock:
                    if request_key in self._pending_requests:
                        future = self._pending_requests[request_key].future
                        del self._pending_requests[request_key]
                        if not future.done():
                            future.set_result(result)

                    # Reset retry count on success
                    if request_key in self._retry_counts:
                        del self._retry_counts[request_key]

                logger.debug(f"Request completed successfully: {request_key}")
                return result

            except Exception as e:
                last_error = e
                attempt += 1

                # Check if we should retry this error
                should_retry = self._should_retry_error(e)

                if attempt > retry_config.max_retries or not should_retry:
                    # Failed permanently
                    async with self._lock:
                        if request_key in self._pending_requests:
                            future = self._pending_requests[request_key].future
                            del self._pending_requests[request_key]
                            if not future.done():
                                future.set_exception(e)

                    error_msg = f"Request failed after {attempt} attempts: {request_key} - {e}"
                    if not should_retry:
                        error_msg += " (non-retryable error)"
                    logger.error(error_msg)
                    raise e

                # Log retry attempt
                logger.warning(f"Request failed, will retry: {request_key} - {e} (attempt {attempt})")

        # Should never reach here
        raise Exception("Unexpected end of retry loop")

    def _should_retry_error(self, error: Exception) -> bool:
        """Determine if an error should be retried."""
        # HTTP errors - check status code
        if hasattr(error, 'response') and hasattr(error.response, 'status_code'):
            status_code = error.response.status_code

            # Retry on server errors and rate limits
            if status_code >= 500:  # 5xx server errors
                return True
            if status_code == 429:  # Rate limit
                return True
            if status_code in [408, 409, 423, 503]:  # Other retryable errors
                return True

            # Don't retry client errors (4xx except above)
            if 400 <= status_code < 500:
                return False

        # Network/connection errors - usually retryable
        if isinstance(error, (asyncio.TimeoutError, ConnectionError)):
            return True

        # Import-time check for httpx errors
        try:
            import httpx
            if isinstance(error, (httpx.TimeoutException, httpx.NetworkError)):
                return True
        except ImportError:
            pass

        # Default to not retry for unknown errors
        return False

    async def get_pending_requests_count(self) -> int:
        """Get the number of currently pending requests."""
        async with self._lock:
            return len(self._pending_requests)

    async def clear_pending_requests(self) -> None:
        """Clear all pending requests (for cleanup)."""
        async with self._lock:
            for request_key, pending in self._pending_requests.items():
                if not pending.future.done():
                    pending.future.cancel()
            self._pending_requests.clear()
            logger.info("Cleared all pending requests")

    def get_stats(self) -> Dict[str, Any]:
        """Get request manager statistics."""
        return {
            "pending_requests": len(self._pending_requests),
            "tracked_endpoints": len(self._last_request_time),
            "retry_counts": dict(self._retry_counts)
        }


# Global request manager instance
request_manager = RequestManager()