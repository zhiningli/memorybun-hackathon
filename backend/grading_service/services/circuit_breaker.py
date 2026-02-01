"""
Circuit Breaker module for inter-service calls.

Provides circuit breaker instances for external service calls to prevent
cascading failures when downstream services are unavailable.

Circuit Breaker States:
- CLOSED: Normal operation, requests pass through
- OPEN: Service is down, requests fail immediately (fail-fast)
- HALF-OPEN: Testing if service recovered, allows limited requests

Configuration:
- fail_max: Number of failures before opening circuit (default: 3)
- reset_timeout: Seconds before attempting recovery (default: 30)
"""

import pybreaker
import logging

logger = logging.getLogger(__name__)


class LoggingListener(pybreaker.CircuitBreakerListener):
    """Logs circuit breaker state transitions."""
    
    def state_change(self, cb: pybreaker.CircuitBreaker, old_state, new_state):
        # States are strings in pybreaker (e.g., 'closed', 'open', 'half-open')
        logger.warning(
            f"Circuit breaker '{cb.name}' state changed: {old_state} -> {new_state}"
        )
    
    def failure(self, cb: pybreaker.CircuitBreaker, exc: Exception):
        logger.warning(f"Circuit breaker '{cb.name}' recorded failure: {exc}")
    
    def success(self, cb: pybreaker.CircuitBreaker):
        logger.debug(f"Circuit breaker '{cb.name}' recorded success")


# Shared listener for all breakers
_logging_listener = LoggingListener()


# Circuit breaker for Question Service calls (rubrics, questions, answers)
question_service_breaker = pybreaker.CircuitBreaker(
    fail_max=3,           # Open after 3 consecutive failures
    reset_timeout=30,     # Try again after 30 seconds
    name="question_service",
    listeners=[_logging_listener],
)

# Circuit breaker for Transcription Service calls (screenshots)
transcription_service_breaker = pybreaker.CircuitBreaker(
    fail_max=3,
    reset_timeout=30,
    name="transcription_service",
    listeners=[_logging_listener],
)
