import pytest
import logging
from fastapi import FastAPI
from fastapi.testclient import TestClient
from middleware.correlation import CorrelationIdMiddleware
from middleware.request_id import get_request_id, set_request_id, _correlation_id_ctx_var
from middleware.log_filter import CorrelationIdFilter

def test_request_id_context_var():
    """Test setting and getting request ID from context var"""
    # Reset context var
    token = _correlation_id_ctx_var.set(None)
    
    try:
        assert get_request_id() == "unknown"
        
        ctx_id = set_request_id("test-id")
        assert ctx_id == "test-id"
        assert get_request_id() == "test-id"
        
        # Test auto-generation
        gen_id = set_request_id(None)
        assert len(gen_id) > 0
        assert gen_id != "test-id"
        assert get_request_id() == gen_id
        
    finally:
        _correlation_id_ctx_var.reset(token)

def test_correlation_id_middleware_generates_id():
    """Test middleware generates ID when missing"""
    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)
    
    @app.get("/")
    def read_root():
        return {"id": get_request_id()}
        
    client = TestClient(app)
    response = client.get("/")
    
    assert response.status_code == 200
    assert "X-Correlation-ID" in response.headers
    generated_id = response.headers["X-Correlation-ID"]
    assert len(generated_id) > 0
    assert response.json()["id"] == generated_id

def test_correlation_id_middleware_propagates_id():
    """Test middleware uses existing ID"""
    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)
    
    @app.get("/")
    def read_root():
        return {"id": get_request_id()}
        
    client = TestClient(app)
    headers = {"X-Correlation-ID": "existing-123"}
    response = client.get("/", headers=headers)
    
    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"] == "existing-123"
    assert response.json()["id"] == "existing-123"

def test_correlation_id_middleware_supports_request_id_header():
    """Test middleware falls back to X-Request-ID"""
    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)
    
    @app.get("/")
    def read_root():
        return {"id": get_request_id()}
        
    client = TestClient(app)
    headers = {"X-Request-ID": "legacy-id-456"}
    response = client.get("/", headers=headers)
    
    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"] == "legacy-id-456"
    assert response.json()["id"] == "legacy-id-456"

def test_log_filter_injects_id():
    """Test CorrelationIdFilter injects ID into log record"""
    # Set a context ID
    token = _correlation_id_ctx_var.set("log-test-id")
    
    try:
        filter = CorrelationIdFilter()
        record = logging.LogRecord("test", logging.INFO, "path", 1, "msg", (), None)
        
        # Verify attribute is missing initially
        assert not hasattr(record, "correlation_id")
        
        # Apply filter
        result = filter.filter(record)
        
        assert result is True
        assert hasattr(record, "correlation_id")
        assert record.correlation_id == "log-test-id"
        
    finally:
        _correlation_id_ctx_var.reset(token)
