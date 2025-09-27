"""Intelligent retry manager with exponential backoff and circuit breaker pattern."""

import asyncio
import time
import random
from typing import Callable, Any, Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging

from error_handler import error_handler, ErrorCategory, ErrorSeverity


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit open, requests fail fast
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 3
    base_delay: float = 1.0  # Base delay in seconds
    max_delay: float = 300.0  # Maximum delay in seconds
    exponential_factor: float = 2.0
    jitter: bool = True
    circuit_breaker_enabled: bool = True
    circuit_failure_threshold: int = 5  # Failures before opening circuit
    circuit_recovery_timeout: int = 60  # Seconds to wait before testing recovery
    circuit_success_threshold: int = 3  # Successes needed to close circuit


@dataclass
class CircuitBreakerState:
    """Circuit breaker state tracking."""
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    next_attempt_time: Optional[datetime] = None


@dataclass
class RetryStats:
    """Statistics for retry operations."""
    total_attempts: int = 0
    successful_attempts: int = 0
    failed_attempts: int = 0
    total_delay_time: float = 0.0
    circuit_opens: int = 0
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None


class IntelligentRetryManager:
    """Intelligent retry manager with circuit breaker and adaptive backoff."""

    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
        self.logger = logging.getLogger(__name__)

        # Circuit breaker states per service endpoint
        self.circuit_breakers: Dict[str, CircuitBreakerState] = {}

        # Retry statistics per service
        self.retry_stats: Dict[str, RetryStats] = {}

        # Recent error patterns for adaptive behavior
        self.error_history: Dict[str, List[datetime]] = {}

    async def execute_with_retry(
        self,
        func: Callable,
        service_key: str,
        *args,
        retry_config: Optional[RetryConfig] = None,
        **kwargs
    ) -> Any:
        """Execute function with intelligent retry logic."""
        config = retry_config or self.config

        # Initialize tracking for this service
        if service_key not in self.circuit_breakers:
            self.circuit_breakers[service_key] = CircuitBreakerState()
            self.retry_stats[service_key] = RetryStats()
            self.error_history[service_key] = []

        circuit = self.circuit_breakers[service_key]
        stats = self.retry_stats[service_key]

        # Check circuit breaker state
        if config.circuit_breaker_enabled:
            if not self._can_execute(circuit, config):
                error_msg = f"Circuit breaker is OPEN for {service_key}. Service appears to be down."
                self.logger.warning(error_msg)
                return f"❌ **Service Unavailable**: {error_msg}\n\n💡 **Suggestion**: The service will be tested again automatically in a few minutes."

        attempt = 0
        last_error = None
        total_delay = 0.0

        while attempt < config.max_retries:
            attempt += 1
            stats.total_attempts += 1

            try:
                # Execute the function
                start_time = time.time()
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time

                # Success - update circuit breaker and stats
                self._record_success(service_key, circuit, stats, execution_time)
                return result

            except Exception as e:
                last_error = e
                execution_time = time.time() - start_time

                # Handle the error and get details
                context = {
                    "service": service_key,
                    "attempt": attempt,
                    "max_retries": config.max_retries,
                    "execution_time": execution_time
                }

                error_details = error_handler.handle_error(e, context, service_key)
                self._record_failure(service_key, circuit, stats, error_details)

                # Check if we should retry
                if not self._should_retry(error_details, attempt, config):
                    break

                # Calculate delay for next attempt
                if attempt < config.max_retries:
                    delay = self._calculate_delay(
                        attempt, config, error_details, service_key
                    )
                    total_delay += delay

                    self.logger.info(
                        f"Retrying {service_key} in {delay:.1f}s (attempt {attempt}/{config.max_retries})"
                    )

                    await asyncio.sleep(delay)

        # All retries exhausted - handle final failure
        stats.failed_attempts += 1
        stats.total_delay_time += total_delay

        if last_error:
            context = {
                "service": service_key,
                "total_attempts": attempt,
                "total_delay": total_delay
            }
            error_details = error_handler.handle_error(last_error, context, service_key)
            return error_handler.format_user_message(error_details)

        return f"❌ **Request Failed**: Maximum retry attempts ({config.max_retries}) exceeded for {service_key}."

    def _can_execute(self, circuit: CircuitBreakerState, config: RetryConfig) -> bool:
        """Check if request can be executed based on circuit breaker state."""
        now = datetime.now()

        if circuit.state == CircuitState.CLOSED:
            return True
        elif circuit.state == CircuitState.OPEN:
            # Check if enough time has passed to attempt recovery
            if (circuit.next_attempt_time and now >= circuit.next_attempt_time):
                circuit.state = CircuitState.HALF_OPEN
                circuit.success_count = 0
                self.logger.info("Circuit breaker moving to HALF_OPEN state")
                return True
            return False
        elif circuit.state == CircuitState.HALF_OPEN:
            # Allow limited requests to test recovery
            return circuit.success_count < config.circuit_success_threshold

        return False

    def _record_success(
        self,
        service_key: str,
        circuit: CircuitBreakerState,
        stats: RetryStats,
        execution_time: float
    ):
        """Record successful execution."""
        stats.successful_attempts += 1
        stats.last_success = datetime.now()

        if circuit.state == CircuitState.HALF_OPEN:
            circuit.success_count += 1
            if circuit.success_count >= self.config.circuit_success_threshold:
                circuit.state = CircuitState.CLOSED
                circuit.failure_count = 0
                self.logger.info(f"Circuit breaker CLOSED for {service_key} - service recovered")
        elif circuit.state == CircuitState.CLOSED:
            # Reset failure count on success
            circuit.failure_count = max(0, circuit.failure_count - 1)

    def _record_failure(
        self,
        service_key: str,
        circuit: CircuitBreakerState,
        stats: RetryStats,
        error_details
    ):
        """Record failed execution."""
        now = datetime.now()
        stats.last_failure = now

        # Add to error history for pattern analysis
        if service_key not in self.error_history:
            self.error_history[service_key] = []

        self.error_history[service_key].append(now)

        # Keep only recent errors (last hour)
        cutoff_time = now - timedelta(hours=1)
        self.error_history[service_key] = [
            ts for ts in self.error_history[service_key] if ts > cutoff_time
        ]

        # Update circuit breaker based on error severity
        if error_details.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            circuit.failure_count += 2  # Count severe errors more heavily
        else:
            circuit.failure_count += 1

        # Check if circuit should open
        if (circuit.state == CircuitState.CLOSED and
            circuit.failure_count >= self.config.circuit_failure_threshold):

            circuit.state = CircuitState.OPEN
            circuit.last_failure_time = now
            circuit.next_attempt_time = now + timedelta(seconds=self.config.circuit_recovery_timeout)
            stats.circuit_opens += 1

            self.logger.warning(
                f"Circuit breaker OPENED for {service_key} - too many failures "
                f"({circuit.failure_count}/{self.config.circuit_failure_threshold})"
            )

        elif circuit.state == CircuitState.HALF_OPEN:
            # Failed during recovery test - back to open
            circuit.state = CircuitState.OPEN
            circuit.next_attempt_time = now + timedelta(seconds=self.config.circuit_recovery_timeout)
            self.logger.warning(f"Circuit breaker back to OPEN for {service_key} - recovery test failed")

    def _should_retry(self, error_details, attempt: int, config: RetryConfig) -> bool:
        """Determine if we should retry based on error details."""
        if attempt >= config.max_retries:
            return False

        # Don't retry non-recoverable errors
        if not error_details.recoverable:
            return False

        # Don't retry authentication errors
        if error_details.category == ErrorCategory.AUTHENTICATION_ERROR:
            return False

        # Don't retry user input errors
        if error_details.category == ErrorCategory.VALIDATION_ERROR:
            return False

        return True

    def _calculate_delay(
        self,
        attempt: int,
        config: RetryConfig,
        error_details,
        service_key: str
    ) -> float:
        """Calculate delay before next retry attempt."""
        # Start with exponential backoff
        delay = min(
            config.base_delay * (config.exponential_factor ** (attempt - 1)),
            config.max_delay
        )

        # Adjust based on error type
        if error_details.category == ErrorCategory.RATE_LIMIT_ERROR:
            # Use the retry-after header if available, or longer delay for rate limits
            if error_details.retry_after:
                delay = max(delay, error_details.retry_after)
            else:
                delay = max(delay, 60)  # Minimum 1 minute for rate limits

        # Adaptive delay based on recent error frequency
        recent_errors = len(self.error_history.get(service_key, []))
        if recent_errors > 10:  # High error rate
            delay *= 1.5  # Increase delay
        elif recent_errors > 20:  # Very high error rate
            delay *= 2.0

        # Add jitter to prevent thundering herd
        if config.jitter:
            jitter_range = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_range, jitter_range)

        return max(delay, 0.1)  # Minimum 100ms delay

    def get_service_health(self, service_key: str) -> Dict[str, Any]:
        """Get health status for a service."""
        if service_key not in self.circuit_breakers:
            return {"status": "unknown", "message": "No data available"}

        circuit = self.circuit_breakers[service_key]
        stats = self.retry_stats[service_key]
        recent_errors = len(self.error_history.get(service_key, []))

        health_status = {
            "status": circuit.state.value,
            "failure_count": circuit.failure_count,
            "success_rate": (
                stats.successful_attempts / max(stats.total_attempts, 1) * 100
                if stats.total_attempts > 0 else 0
            ),
            "recent_error_count": recent_errors,
            "last_success": stats.last_success.isoformat() if stats.last_success else None,
            "last_failure": stats.last_failure.isoformat() if stats.last_failure else None,
            "circuit_opens": stats.circuit_opens,
            "average_delay": (
                stats.total_delay_time / max(stats.failed_attempts, 1)
                if stats.failed_attempts > 0 else 0
            )
        }

        # Add status message
        if circuit.state == CircuitState.OPEN:
            health_status["message"] = "Service is currently unavailable (circuit breaker open)"
        elif circuit.state == CircuitState.HALF_OPEN:
            health_status["message"] = "Service is being tested for recovery"
        elif recent_errors > 10:
            health_status["message"] = "Service is experiencing high error rates"
        elif stats.success_rate > 95:
            health_status["message"] = "Service is healthy"
        else:
            health_status["message"] = "Service has some issues but is operational"

        return health_status

    def get_all_services_health(self) -> Dict[str, Dict[str, Any]]:
        """Get health status for all monitored services."""
        return {
            service: self.get_service_health(service)
            for service in self.circuit_breakers.keys()
        }

    def reset_circuit_breaker(self, service_key: str):
        """Manually reset circuit breaker for a service (for testing/maintenance)."""
        if service_key in self.circuit_breakers:
            circuit = self.circuit_breakers[service_key]
            circuit.state = CircuitState.CLOSED
            circuit.failure_count = 0
            circuit.success_count = 0
            circuit.next_attempt_time = None
            self.logger.info(f"Circuit breaker manually reset for {service_key}")

    def clear_error_history(self, service_key: str):
        """Clear error history for a service."""
        if service_key in self.error_history:
            self.error_history[service_key] = []
            self.logger.info(f"Error history cleared for {service_key}")


# Global retry manager instance
retry_manager = IntelligentRetryManager()


def with_retry(service_key: str, config: Optional[RetryConfig] = None):
    """Decorator to add intelligent retry to async functions."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            return await retry_manager.execute_with_retry(
                func, service_key, *args, retry_config=config, **kwargs
            )
        return wrapper
    return decorator