"""Enhanced error handling system with detailed user messages and recovery."""

import logging
import traceback
from typing import Dict, Any, Optional, Union
from enum import Enum
from dataclasses import dataclass
from datetime import datetime


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for better classification."""
    API_ERROR = "api_error"
    NETWORK_ERROR = "network_error"
    AUTHENTICATION_ERROR = "authentication_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    PARSING_ERROR = "parsing_error"
    CACHE_ERROR = "cache_error"
    VALIDATION_ERROR = "validation_error"
    SYSTEM_ERROR = "system_error"
    USER_ERROR = "user_error"


@dataclass
class ErrorDetails:
    """Detailed error information."""
    message: str
    category: ErrorCategory
    severity: ErrorSeverity
    source: str
    timestamp: datetime
    user_message: str
    suggestions: list[str]
    recoverable: bool = True
    retry_after: Optional[int] = None
    technical_details: Optional[str] = None


class EnhancedErrorHandler:
    """Enhanced error handler with detailed messages and recovery suggestions."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.error_patterns = self._initialize_error_patterns()

    def _initialize_error_patterns(self) -> Dict[str, ErrorDetails]:
        """Initialize common error patterns with detailed responses."""
        return {
            # Network errors
            "connection_timeout": ErrorDetails(
                message="Connection timeout occurred",
                category=ErrorCategory.NETWORK_ERROR,
                severity=ErrorSeverity.MEDIUM,
                source="network",
                timestamp=datetime.now(),
                user_message="The request timed out while connecting to the academic database. This is usually temporary.",
                suggestions=[
                    "Wait a moment and try again",
                    "Check your internet connection",
                    "Try searching for fewer results or a simpler query"
                ],
                recoverable=True,
                retry_after=30
            ),

            "connection_refused": ErrorDetails(
                message="Connection refused by server",
                category=ErrorCategory.NETWORK_ERROR,
                severity=ErrorSeverity.HIGH,
                source="network",
                timestamp=datetime.now(),
                user_message="Unable to connect to the academic database. The service may be temporarily unavailable.",
                suggestions=[
                    "Wait a few minutes and try again",
                    "Check if the service is experiencing downtime",
                    "Try using a different data source if available"
                ],
                recoverable=True,
                retry_after=300
            ),

            # API errors
            "rate_limit_exceeded": ErrorDetails(
                message="API rate limit exceeded",
                category=ErrorCategory.RATE_LIMIT_ERROR,
                severity=ErrorSeverity.MEDIUM,
                source="api",
                timestamp=datetime.now(),
                user_message="You've made too many requests too quickly. Please wait before trying again.",
                suggestions=[
                    "Wait for the rate limit to reset",
                    "Reduce the frequency of your requests",
                    "Consider using cached results when available"
                ],
                recoverable=True,
                retry_after=60
            ),

            "unauthorized": ErrorDetails(
                message="Authentication failed",
                category=ErrorCategory.AUTHENTICATION_ERROR,
                severity=ErrorSeverity.HIGH,
                source="api",
                timestamp=datetime.now(),
                user_message="Authentication failed. Your API credentials may be invalid or expired.",
                suggestions=[
                    "Check your API key configuration",
                    "Verify that your API key is still valid",
                    "Contact the service provider if the issue persists"
                ],
                recoverable=False
            ),

            "service_unavailable": ErrorDetails(
                message="Service temporarily unavailable",
                category=ErrorCategory.API_ERROR,
                severity=ErrorSeverity.HIGH,
                source="api",
                timestamp=datetime.now(),
                user_message="The academic database service is temporarily unavailable.",
                suggestions=[
                    "Try again in a few minutes",
                    "Use alternative data sources if available",
                    "Check the service status page for updates"
                ],
                recoverable=True,
                retry_after=600
            ),

            # Parsing errors
            "invalid_json": ErrorDetails(
                message="Invalid JSON response",
                category=ErrorCategory.PARSING_ERROR,
                severity=ErrorSeverity.MEDIUM,
                source="parsing",
                timestamp=datetime.now(),
                user_message="Received an invalid response from the academic database. This may be a temporary issue.",
                suggestions=[
                    "Try the request again",
                    "Simplify your search query",
                    "Contact support if the problem continues"
                ],
                recoverable=True
            ),

            "malformed_data": ErrorDetails(
                message="Malformed data received",
                category=ErrorCategory.PARSING_ERROR,
                severity=ErrorSeverity.MEDIUM,
                source="parsing",
                timestamp=datetime.now(),
                user_message="The academic database returned data in an unexpected format.",
                suggestions=[
                    "Try a different search query",
                    "Wait and try again later",
                    "Use a different data source if available"
                ],
                recoverable=True
            ),

            # Validation errors
            "invalid_query": ErrorDetails(
                message="Invalid search query",
                category=ErrorCategory.VALIDATION_ERROR,
                severity=ErrorSeverity.LOW,
                source="validation",
                timestamp=datetime.now(),
                user_message="Your search query contains invalid parameters or formatting.",
                suggestions=[
                    "Check your query for special characters or syntax errors",
                    "Try a simpler query",
                    "Refer to the search syntax documentation"
                ],
                recoverable=True
            ),

            "missing_required_param": ErrorDetails(
                message="Missing required parameter",
                category=ErrorCategory.VALIDATION_ERROR,
                severity=ErrorSeverity.LOW,
                source="validation",
                timestamp=datetime.now(),
                user_message="Required information is missing from your request.",
                suggestions=[
                    "Provide all required parameters",
                    "Check the documentation for required fields",
                    "Verify your input data is complete"
                ],
                recoverable=True
            ),

            # Cache errors
            "cache_unavailable": ErrorDetails(
                message="Cache system unavailable",
                category=ErrorCategory.CACHE_ERROR,
                severity=ErrorSeverity.LOW,
                source="cache",
                timestamp=datetime.now(),
                user_message="The cache system is temporarily unavailable, but searches will continue normally.",
                suggestions=[
                    "Your searches may be slightly slower",
                    "Results will still be retrieved from academic databases",
                    "Cache functionality will be restored automatically"
                ],
                recoverable=True
            ),

            "cache_corruption": ErrorDetails(
                message="Cache data corrupted",
                category=ErrorCategory.CACHE_ERROR,
                severity=ErrorSeverity.MEDIUM,
                source="cache",
                timestamp=datetime.now(),
                user_message="Cached data appears to be corrupted and has been cleared.",
                suggestions=[
                    "Fresh data will be retrieved from academic databases",
                    "Performance may be slower until cache rebuilds",
                    "The issue should resolve automatically"
                ],
                recoverable=True
            )
        }

    def handle_error(
        self,
        error: Exception,
        context: Dict[str, Any],
        source: str = "unknown"
    ) -> ErrorDetails:
        """Handle an error and return detailed error information."""
        error_type = type(error).__name__
        error_message = str(error).lower()

        # Try to match against known error patterns
        error_details = self._match_error_pattern(error, error_message, source)

        # If no specific pattern matched, create a generic error
        if not error_details:
            error_details = self._create_generic_error(error, source)

        # Update timestamp and add context
        error_details.timestamp = datetime.now()
        error_details.technical_details = self._get_technical_details(error, context)

        # Log the error
        self._log_error(error_details, error, context)

        return error_details

    def _match_error_pattern(
        self,
        error: Exception,
        error_message: str,
        source: str
    ) -> Optional[ErrorDetails]:
        """Match error against known patterns."""
        error_type = type(error).__name__

        # HTTP/Network specific errors
        if "timeout" in error_message or "timed out" in error_message:
            details = self.error_patterns["connection_timeout"]
            details.source = source
            return details

        if "connection refused" in error_message or "refused" in error_message:
            details = self.error_patterns["connection_refused"]
            details.source = source
            return details

        if "429" in error_message or "rate limit" in error_message:
            details = self.error_patterns["rate_limit_exceeded"]
            details.source = source
            return details

        if "401" in error_message or "unauthorized" in error_message:
            details = self.error_patterns["unauthorized"]
            details.source = source
            return details

        if "503" in error_message or "service unavailable" in error_message:
            details = self.error_patterns["service_unavailable"]
            details.source = source
            return details

        # JSON/Parsing errors
        if "json" in error_message and ("decode" in error_message or "invalid" in error_message):
            details = self.error_patterns["invalid_json"]
            details.source = source
            return details

        # Validation errors
        if error_type in ["ValueError", "ValidationError"]:
            if "required" in error_message or "missing" in error_message:
                details = self.error_patterns["missing_required_param"]
                details.source = source
                return details
            else:
                details = self.error_patterns["invalid_query"]
                details.source = source
                return details

        return None

    def _create_generic_error(self, error: Exception, source: str) -> ErrorDetails:
        """Create a generic error response for unknown errors."""
        return ErrorDetails(
            message=f"Unexpected error: {type(error).__name__}",
            category=ErrorCategory.SYSTEM_ERROR,
            severity=ErrorSeverity.MEDIUM,
            source=source,
            timestamp=datetime.now(),
            user_message="An unexpected error occurred while processing your request.",
            suggestions=[
                "Try your request again",
                "Simplify your search parameters",
                "Wait a moment and retry",
                "Contact support if the problem persists"
            ],
            recoverable=True,
            technical_details=str(error)
        )

    def _get_technical_details(self, error: Exception, context: Dict[str, Any]) -> str:
        """Generate technical details for debugging."""
        details = [
            f"Error Type: {type(error).__name__}",
            f"Error Message: {str(error)}",
            f"Context: {context}",
        ]

        # Add stack trace for debugging
        if hasattr(error, "__traceback__") and error.__traceback__:
            details.append("Stack Trace:")
            details.extend(traceback.format_tb(error.__traceback__))

        return "\n".join(details)

    def _log_error(self, error_details: ErrorDetails, error: Exception, context: Dict[str, Any]):
        """Log error with appropriate severity level."""
        log_message = (
            f"[{error_details.source}] {error_details.category.value}: {error_details.message}"
        )

        if error_details.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message, exc_info=error, extra={"context": context})
        elif error_details.severity == ErrorSeverity.HIGH:
            self.logger.error(log_message, exc_info=error, extra={"context": context})
        elif error_details.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message, extra={"context": context})
        else:
            self.logger.info(log_message, extra={"context": context})

    def format_user_message(self, error_details: ErrorDetails) -> str:
        """Format error details into a user-friendly message."""
        message_parts = [
            f"❌ **Error**: {error_details.user_message}",
            ""
        ]

        if error_details.suggestions:
            message_parts.append("💡 **Suggestions**:")
            for suggestion in error_details.suggestions:
                message_parts.append(f"• {suggestion}")
            message_parts.append("")

        if error_details.retry_after:
            if error_details.retry_after < 120:
                wait_time = f"{error_details.retry_after} seconds"
            else:
                wait_time = f"{error_details.retry_after // 60} minutes"
            message_parts.append(f"⏱️ **Recommended wait time**: {wait_time}")
            message_parts.append("")

        if error_details.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            message_parts.append("🔧 **Status**: This appears to be a service-related issue that should resolve automatically.")

        return "\n".join(message_parts)

    def is_recoverable(self, error_details: ErrorDetails) -> bool:
        """Check if an error is recoverable."""
        return error_details.recoverable and error_details.category not in [
            ErrorCategory.AUTHENTICATION_ERROR,
            ErrorCategory.VALIDATION_ERROR
        ]

    def get_retry_strategy(self, error_details: ErrorDetails) -> Dict[str, Union[bool, int]]:
        """Get retry strategy for an error."""
        if not self.is_recoverable(error_details):
            return {"should_retry": False}

        retry_delays = {
            ErrorCategory.RATE_LIMIT_ERROR: 60,
            ErrorCategory.NETWORK_ERROR: 30,
            ErrorCategory.API_ERROR: 120,
            ErrorCategory.CACHE_ERROR: 0,  # Immediate retry for cache errors
            ErrorCategory.PARSING_ERROR: 10,
        }

        delay = retry_delays.get(error_details.category, 30)
        if error_details.retry_after:
            delay = max(delay, error_details.retry_after)

        return {
            "should_retry": True,
            "delay_seconds": delay,
            "max_retries": 3 if error_details.category != ErrorCategory.RATE_LIMIT_ERROR else 1
        }


# Global error handler instance
error_handler = EnhancedErrorHandler()


def handle_api_error(func):
    """Decorator to handle API errors with enhanced error reporting."""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            context = {
                "function": func.__name__,
                "args": str(args)[:200],  # Limit length
                "kwargs": {k: str(v)[:100] for k, v in kwargs.items()}  # Limit length
            }

            error_details = error_handler.handle_error(e, context, func.__name__)
            user_message = error_handler.format_user_message(error_details)

            # Return error message instead of raising
            return user_message

    return wrapper