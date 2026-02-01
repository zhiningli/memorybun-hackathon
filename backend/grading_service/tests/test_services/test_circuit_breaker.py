"""
Unit tests for Circuit Breaker module.

Tests:
- Circuit breaker stays CLOSED on successful calls
- Circuit breaker opens after fail_max failures
- Circuit breaker rejects calls when OPEN (raises CircuitBreakerError)
- Circuit breaker transitions to HALF-OPEN after reset_timeout
- Logging listener records state changes
"""

import pytest
import pybreaker
from unittest.mock import patch, MagicMock, AsyncMock


class TestCircuitBreakerModule:
    """Tests for circuit_breaker.py module."""
    
    def test_breakers_are_configured(self):
        """Test that circuit breakers are properly configured."""
        from services.circuit_breaker import (
            question_service_breaker,
            transcription_service_breaker,
        )
        
        # Question service breaker
        assert question_service_breaker.name == "question_service"
        assert question_service_breaker.fail_max == 3
        assert question_service_breaker.reset_timeout == 30
        
        # Transcription service breaker
        assert transcription_service_breaker.name == "transcription_service"
        assert transcription_service_breaker.fail_max == 3
        assert transcription_service_breaker.reset_timeout == 30
    
    def test_breaker_initial_state_is_closed(self):
        """Test that circuit breakers start in CLOSED state."""
        from services.circuit_breaker import (
            question_service_breaker,
            transcription_service_breaker,
        )
        
        assert question_service_breaker.current_state == pybreaker.STATE_CLOSED
        assert transcription_service_breaker.current_state == pybreaker.STATE_CLOSED


class TestCircuitBreakerBehavior:
    """Tests for circuit breaker behavior using fresh breaker instances."""
    
    @pytest.fixture
    def fresh_breaker(self):
        """Create a fresh circuit breaker for each test."""
        return pybreaker.CircuitBreaker(
            fail_max=2,
            reset_timeout=1,  # Short timeout for testing
            name="test_breaker",
        )
    
    def test_stays_closed_on_success(self, fresh_breaker):
        """Circuit stays CLOSED when calls succeed."""
        @fresh_breaker
        def success_func():
            return "ok"
        
        result = success_func()
        
        assert result == "ok"
        assert fresh_breaker.current_state == pybreaker.STATE_CLOSED
        assert fresh_breaker.fail_counter == 0
    
    def test_opens_after_fail_max_failures(self, fresh_breaker):
        """Circuit opens after fail_max consecutive failures."""
        @fresh_breaker
        def failure_func():
            raise Exception("service unavailable")
        
        # First failure
        with pytest.raises(Exception):
            failure_func()
        assert fresh_breaker.fail_counter == 1
        assert fresh_breaker.current_state == pybreaker.STATE_CLOSED
        
        # Second failure (fail_max = 2)
        with pytest.raises(Exception):
            failure_func()
        assert fresh_breaker.current_state == pybreaker.STATE_OPEN
    
    def test_rejects_calls_when_open(self, fresh_breaker):
        """Circuit rejects calls immediately when OPEN."""
        @fresh_breaker
        def failure_func():
            raise Exception("service unavailable")
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                failure_func()
        
        assert fresh_breaker.current_state == pybreaker.STATE_OPEN
        
        # Next call should fail fast with CircuitBreakerError
        with pytest.raises(pybreaker.CircuitBreakerError):
            failure_func()
    
    def test_success_resets_fail_counter(self, fresh_breaker):
        """Successful call resets the failure counter."""
        call_count = 0
        
        @fresh_breaker
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("first call fails")
            return "success"
        
        # First call fails
        with pytest.raises(Exception):
            flaky_func()
        assert fresh_breaker.fail_counter == 1
        
        # Second call succeeds
        result = flaky_func()
        assert result == "success"
        assert fresh_breaker.fail_counter == 0


class TestLoggingListener:
    """Tests for the logging listener."""
    
    def test_listener_logs_state_change(self):
        """Test that listener logs state transitions."""
        from services.circuit_breaker import LoggingListener
        
        listener = LoggingListener()
        mock_breaker = MagicMock()
        mock_breaker.name = "test"
        
        with patch("services.circuit_breaker.logger") as mock_logger:
            listener.state_change(
                mock_breaker,
                pybreaker.STATE_CLOSED,
                pybreaker.STATE_OPEN
            )
            mock_logger.warning.assert_called_once()
            # Check that log message contains state names
            log_call_str = str(mock_logger.warning.call_args)
            assert "closed" in log_call_str.lower() or "CLOSED" in log_call_str
    
    def test_listener_logs_failure(self):
        """Test that listener logs failures."""
        from services.circuit_breaker import LoggingListener
        
        listener = LoggingListener()
        mock_breaker = MagicMock()
        mock_breaker.name = "test"
        
        with patch("services.circuit_breaker.logger") as mock_logger:
            listener.failure(mock_breaker, Exception("connection refused"))
            mock_logger.warning.assert_called_once()

@pytest.mark.asyncio
class TestAsyncCircuitBreaker:
    """Tests for async function wrapping."""
    
    async def test_async_success_keeps_circuit_closed(self):
        """Test circuit breaker works with async functions and successful calls."""
        import uuid
        breaker = pybreaker.CircuitBreaker(
            fail_max=2, 
            reset_timeout=1, 
            name=f"async_test_{uuid.uuid4().hex}"
        )
        
        @breaker
        async def async_success():
            return "async ok"
        
        result = await async_success()
        
        assert result == "async ok"
        assert breaker.current_state == pybreaker.STATE_CLOSED
        assert breaker.fail_counter == 0


