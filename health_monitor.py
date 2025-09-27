"""Service health monitoring system for academic data sources."""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import json
import logging

from retry_manager import retry_manager
from error_handler import error_handler


class ServiceStatus(Enum):
    """Service health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DOWN = "down"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Individual health check result."""
    service: str
    status: ServiceStatus
    response_time: float
    timestamp: datetime
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ServiceMetrics:
    """Metrics for a service over time."""
    service: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0
    uptime_percentage: float = 0.0
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0


class HealthMonitor:
    """Comprehensive health monitoring system for academic data sources."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Health check results history
        self.health_history: Dict[str, List[HealthCheck]] = {}

        # Service metrics
        self.service_metrics: Dict[str, ServiceMetrics] = {}

        # Monitoring configuration
        self.services = {
            "arxiv": {
                "name": "arXiv API",
                "endpoint": "https://export.arxiv.org/api/query",
                "check_interval": 300,  # 5 minutes
                "timeout": 10,
                "expected_status": 200
            },
            "semantic_scholar": {
                "name": "Semantic Scholar API",
                "endpoint": "https://api.semanticscholar.org/graph/v1/paper/search",
                "check_interval": 300,
                "timeout": 10,
                "expected_status": 200
            },
            "google_scholar": {
                "name": "Google Scholar",
                "endpoint": "https://scholar.google.com",
                "check_interval": 600,  # 10 minutes (more conservative due to scraping)
                "timeout": 15,
                "expected_status": 200
            },
            "cache_system": {
                "name": "Cache System",
                "type": "internal",
                "check_interval": 180,  # 3 minutes
                "timeout": 5
            }
        }

        # Monitoring state
        self.monitoring_active = False
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}

    async def start_monitoring(self):
        """Start health monitoring for all services."""
        if self.monitoring_active:
            self.logger.warning("Health monitoring is already active")
            return

        self.monitoring_active = True
        self.logger.info("Starting health monitoring for all services")

        # Start monitoring tasks for each service
        for service_key, config in self.services.items():
            task = asyncio.create_task(
                self._monitor_service(service_key, config)
            )
            self.monitoring_tasks[service_key] = task

        self.logger.info(f"Started monitoring {len(self.services)} services")

    async def stop_monitoring(self):
        """Stop all health monitoring."""
        if not self.monitoring_active:
            return

        self.monitoring_active = False
        self.logger.info("Stopping health monitoring")

        # Cancel all monitoring tasks
        for service_key, task in self.monitoring_tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        self.monitoring_tasks.clear()
        self.logger.info("Health monitoring stopped")

    async def _monitor_service(self, service_key: str, config: Dict[str, Any]):
        """Monitor a single service continuously."""
        self.logger.info(f"Starting monitoring for {service_key}")

        # Initialize metrics
        if service_key not in self.service_metrics:
            self.service_metrics[service_key] = ServiceMetrics(service=service_key)

        if service_key not in self.health_history:
            self.health_history[service_key] = []

        while self.monitoring_active:
            try:
                # Perform health check
                health_check = await self._perform_health_check(service_key, config)

                # Update metrics and history
                self._update_metrics(service_key, health_check)
                self._add_to_history(service_key, health_check)

                # Log significant status changes
                self._log_status_changes(service_key, health_check)

                # Wait for next check
                await asyncio.sleep(config.get("check_interval", 300))

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error monitoring {service_key}: {e}")
                await asyncio.sleep(60)  # Wait before retrying

    async def _perform_health_check(
        self,
        service_key: str,
        config: Dict[str, Any]
    ) -> HealthCheck:
        """Perform health check for a specific service."""
        start_time = time.time()

        try:
            if config.get("type") == "internal":
                # Internal service check (e.g., cache system)
                status, message, details = await self._check_internal_service(service_key)
            else:
                # External API check
                status, message, details = await self._check_external_service(service_key, config)

            response_time = time.time() - start_time

            return HealthCheck(
                service=service_key,
                status=status,
                response_time=response_time,
                timestamp=datetime.now(),
                message=message,
                details=details
            )

        except Exception as e:
            response_time = time.time() - start_time
            error_details = error_handler.handle_error(e, {"service": service_key}, service_key)

            return HealthCheck(
                service=service_key,
                status=ServiceStatus.DOWN,
                response_time=response_time,
                timestamp=datetime.now(),
                message=f"Health check failed: {str(e)}",
                details={"error": str(e), "error_category": error_details.category.value}
            )

    async def _check_external_service(
        self,
        service_key: str,
        config: Dict[str, Any]
    ) -> tuple[ServiceStatus, str, Dict[str, Any]]:
        """Check external API service health."""
        import httpx

        endpoint = config["endpoint"]
        timeout = config.get("timeout", 10)
        expected_status = config.get("expected_status", 200)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                # Customize request based on service
                if service_key == "arxiv":
                    # Simple query to test arXiv API
                    response = await client.get(
                        endpoint,
                        params={"search_query": "all:electron", "max_results": 1}
                    )
                elif service_key == "semantic_scholar":
                    # Test Semantic Scholar API
                    response = await client.get(
                        endpoint,
                        params={"query": "machine learning", "limit": 1}
                    )
                elif service_key == "google_scholar":
                    # Simple GET to check if Google Scholar is accessible
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    }
                    response = await client.get(endpoint, headers=headers)
                else:
                    # Generic endpoint check
                    response = await client.get(endpoint)

                # Analyze response
                if response.status_code == expected_status:
                    # Additional checks based on service type
                    if service_key == "google_scholar":
                        # Check for CAPTCHA or blocking
                        if "captcha" in response.text.lower() or "unusual traffic" in response.text.lower():
                            return (
                                ServiceStatus.DEGRADED,
                                "Service accessible but showing CAPTCHA/blocking",
                                {"status_code": response.status_code, "captcha_detected": True}
                            )

                    return (
                        ServiceStatus.HEALTHY,
                        f"Service responding normally (HTTP {response.status_code})",
                        {
                            "status_code": response.status_code,
                            "response_size": len(response.content),
                            "content_type": response.headers.get("content-type", "unknown")
                        }
                    )

                elif 500 <= response.status_code < 600:
                    return (
                        ServiceStatus.DOWN,
                        f"Server error (HTTP {response.status_code})",
                        {"status_code": response.status_code}
                    )
                elif response.status_code == 429:
                    return (
                        ServiceStatus.DEGRADED,
                        "Rate limited but service is available",
                        {"status_code": response.status_code}
                    )
                else:
                    return (
                        ServiceStatus.UNHEALTHY,
                        f"Unexpected response (HTTP {response.status_code})",
                        {"status_code": response.status_code}
                    )

        except httpx.TimeoutException:
            return (
                ServiceStatus.UNHEALTHY,
                "Request timed out",
                {"timeout": timeout}
            )
        except httpx.ConnectError:
            return (
                ServiceStatus.DOWN,
                "Connection failed",
                {"error_type": "connection_error"}
            )

    async def _check_internal_service(
        self,
        service_key: str
    ) -> tuple[ServiceStatus, str, Dict[str, Any]]:
        """Check internal service health (e.g., cache system)."""
        if service_key == "cache_system":
            try:
                # Import here to avoid circular imports
                from server import cache_manager

                if cache_manager:
                    # Test cache connectivity
                    stats = await cache_manager.get_cache_stats()
                    if stats:
                        return (
                            ServiceStatus.HEALTHY,
                            "Cache system operational",
                            {
                                "total_entries": stats.get("total_entries", 0),
                                "hit_rate": stats.get("hit_rate", 0.0),
                                "size_mb": stats.get("total_size_mb", 0.0)
                            }
                        )
                    else:
                        return (
                            ServiceStatus.DEGRADED,
                            "Cache system responding but no stats available",
                            {}
                        )
                else:
                    return (
                        ServiceStatus.DOWN,
                        "Cache manager not initialized",
                        {}
                    )
            except Exception as e:
                return (
                    ServiceStatus.UNHEALTHY,
                    f"Cache system error: {str(e)}",
                    {"error": str(e)}
                )

        return (
            ServiceStatus.UNKNOWN,
            f"Unknown internal service: {service_key}",
            {}
        )

    def _update_metrics(self, service_key: str, health_check: HealthCheck):
        """Update service metrics based on health check result."""
        metrics = self.service_metrics[service_key]
        metrics.total_requests += 1

        if health_check.status in [ServiceStatus.HEALTHY, ServiceStatus.DEGRADED]:
            metrics.successful_requests += 1
            metrics.last_success = health_check.timestamp
            metrics.consecutive_successes += 1
            metrics.consecutive_failures = 0
        else:
            metrics.failed_requests += 1
            metrics.last_failure = health_check.timestamp
            metrics.consecutive_failures += 1
            metrics.consecutive_successes = 0

        # Update average response time (exponential moving average)
        if metrics.average_response_time == 0:
            metrics.average_response_time = health_check.response_time
        else:
            # Weight new response time at 10%
            metrics.average_response_time = (
                0.9 * metrics.average_response_time + 0.1 * health_check.response_time
            )

        # Update uptime percentage
        if metrics.total_requests > 0:
            metrics.uptime_percentage = (metrics.successful_requests / metrics.total_requests) * 100

    def _add_to_history(self, service_key: str, health_check: HealthCheck):
        """Add health check to history and maintain size limit."""
        history = self.health_history[service_key]
        history.append(health_check)

        # Keep only last 100 checks per service
        if len(history) > 100:
            history.pop(0)

    def _log_status_changes(self, service_key: str, health_check: HealthCheck):
        """Log significant status changes."""
        history = self.health_history[service_key]

        # Check if status changed from last check
        if len(history) > 1:
            previous_status = history[-2].status
            current_status = health_check.status

            if previous_status != current_status:
                self.logger.info(
                    f"Service {service_key} status changed: "
                    f"{previous_status.value} → {current_status.value} "
                    f"({health_check.message})"
                )

    def get_service_status(self, service_key: str) -> Dict[str, Any]:
        """Get current status for a specific service."""
        if service_key not in self.service_metrics:
            return {"error": f"Service {service_key} not monitored"}

        metrics = self.service_metrics[service_key]
        history = self.health_history.get(service_key, [])

        # Get latest health check
        latest_check = history[-1] if history else None

        # Combine with retry manager health data
        retry_health = retry_manager.get_service_health(service_key)

        status_data = {
            "service": service_key,
            "name": self.services.get(service_key, {}).get("name", service_key),
            "current_status": latest_check.status.value if latest_check else "unknown",
            "last_check": latest_check.timestamp.isoformat() if latest_check else None,
            "message": latest_check.message if latest_check else "No checks performed",
            "response_time": latest_check.response_time if latest_check else 0,
            "uptime_percentage": round(metrics.uptime_percentage, 2),
            "total_requests": metrics.total_requests,
            "successful_requests": metrics.successful_requests,
            "failed_requests": metrics.failed_requests,
            "average_response_time": round(metrics.average_response_time, 3),
            "consecutive_failures": metrics.consecutive_failures,
            "consecutive_successes": metrics.consecutive_successes,
            "last_success": metrics.last_success.isoformat() if metrics.last_success else None,
            "last_failure": metrics.last_failure.isoformat() if metrics.last_failure else None,
        }

        # Add retry manager data
        status_data.update({
            "circuit_breaker_status": retry_health.get("status", "unknown"),
            "circuit_failure_count": retry_health.get("failure_count", 0),
            "success_rate": round(retry_health.get("success_rate", 0), 2),
            "recent_error_count": retry_health.get("recent_error_count", 0)
        })

        return status_data

    def get_overall_health(self) -> Dict[str, Any]:
        """Get overall system health summary."""
        all_services = {}
        overall_status = ServiceStatus.HEALTHY
        total_uptime = 0
        service_count = 0

        for service_key in self.services:
            service_status = self.get_service_status(service_key)
            all_services[service_key] = service_status

            # Determine overall status (worst case)
            current_status = ServiceStatus(service_status.get("current_status", "unknown"))
            if current_status == ServiceStatus.DOWN:
                overall_status = ServiceStatus.DOWN
            elif current_status == ServiceStatus.UNHEALTHY and overall_status != ServiceStatus.DOWN:
                overall_status = ServiceStatus.UNHEALTHY
            elif current_status == ServiceStatus.DEGRADED and overall_status == ServiceStatus.HEALTHY:
                overall_status = ServiceStatus.DEGRADED

            # Calculate average uptime
            uptime = service_status.get("uptime_percentage", 0)
            total_uptime += uptime
            service_count += 1

        average_uptime = total_uptime / service_count if service_count > 0 else 0

        return {
            "overall_status": overall_status.value,
            "average_uptime": round(average_uptime, 2),
            "services": all_services,
            "monitoring_active": self.monitoring_active,
            "last_updated": datetime.now().isoformat()
        }

    def get_health_history(self, service_key: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get health check history for a service."""
        if service_key not in self.health_history:
            return []

        cutoff_time = datetime.now() - timedelta(hours=hours)
        history = self.health_history[service_key]

        filtered_history = [
            {
                "timestamp": check.timestamp.isoformat(),
                "status": check.status.value,
                "response_time": round(check.response_time, 3),
                "message": check.message,
                "details": check.details
            }
            for check in history
            if check.timestamp >= cutoff_time
        ]

        return sorted(filtered_history, key=lambda x: x["timestamp"])

    async def force_health_check(self, service_key: str) -> Dict[str, Any]:
        """Force an immediate health check for a service."""
        if service_key not in self.services:
            return {"error": f"Unknown service: {service_key}"}

        config = self.services[service_key]
        health_check = await self._perform_health_check(service_key, config)

        # Update metrics and history
        self._update_metrics(service_key, health_check)
        self._add_to_history(service_key, health_check)

        return {
            "service": service_key,
            "status": health_check.status.value,
            "response_time": round(health_check.response_time, 3),
            "message": health_check.message,
            "timestamp": health_check.timestamp.isoformat(),
            "details": health_check.details
        }


# Global health monitor instance
health_monitor = HealthMonitor()