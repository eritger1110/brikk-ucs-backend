"""
Integration Execution Engine (IEE)

Executes integration API calls on behalf of agents and workflows.
Handles authentication, request transformation, response parsing, and error handling.

Endpoints:
- POST /api/v1/integrations/{integration_id}/execute - Execute integration endpoint
- GET /api/v1/integrations/{integration_id}/executions - Get execution history
- GET /api/v1/executions/{execution_id} - Get execution details
"""

import httpx
import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from fastapi import HTTPException
from enum import Enum


# ============================================================================
# MODELS
# ============================================================================

class AuthType(str, Enum):
    """Authentication types"""
    NONE = "none"
    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    OAUTH2 = "oauth2"
    BASIC_AUTH = "basic_auth"
    CUSTOM = "custom"


class ExecutionStatus(str, Enum):
    """Execution status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"


class AuthConfig(BaseModel):
    """Authentication configuration"""
    type: AuthType
    api_key: Optional[str] = None
    api_key_header: Optional[str] = "Authorization"
    bearer_token: Optional[str] = None
    oauth2_access_token: Optional[str] = None
    basic_username: Optional[str] = None
    basic_password: Optional[str] = None
    custom_headers: Optional[Dict[str, str]] = Field(default_factory=dict)


class ExecuteIntegrationRequest(BaseModel):
    """Request to execute integration endpoint"""
    endpoint_id: str
    params: Optional[Dict[str, Any]] = Field(default_factory=dict)
    body: Optional[Dict[str, Any]] = Field(default_factory=dict)
    headers: Optional[Dict[str, str]] = Field(default_factory=dict)
    auth: Optional[AuthConfig] = None
    timeout: int = 30


class ExecutionResult(BaseModel):
    """Execution result"""
    execution_id: str
    integration_id: str
    endpoint_id: str
    status: ExecutionStatus
    request: Dict[str, Any]
    response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: int
    executed_at: str
    executed_by: str


# ============================================================================
# INTEGRATION EXECUTION ENGINE
# ============================================================================

class IntegrationExecutionEngine:
    """Executes integration API calls"""
    
    def __init__(self):
        self.executions: Dict[str, ExecutionResult] = {}
        self.rate_limits: Dict[str, List[float]] = {}  # integration_id -> timestamps
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def execute(
        self,
        integration_id: str,
        request: ExecuteIntegrationRequest,
        user_id: str,
        connector_definition: Dict[str, Any]
    ) -> ExecutionResult:
        """Execute integration endpoint"""
        
        # Generate execution ID
        execution_id = f"exec_{int(time.time() * 1000)}"
        
        # Check rate limits
        if self._is_rate_limited(integration_id):
            return ExecutionResult(
                execution_id=execution_id,
                integration_id=integration_id,
                endpoint_id=request.endpoint_id,
                status=ExecutionStatus.RATE_LIMITED,
                request=request.dict(),
                error="Rate limit exceeded. Please try again later.",
                duration_ms=0,
                executed_at=datetime.utcnow().isoformat(),
                executed_by=user_id
            )
        
        # Find endpoint definition
        endpoint = self._find_endpoint(connector_definition, request.endpoint_id)
        if not endpoint:
            raise HTTPException(status_code=404, detail=f"Endpoint {request.endpoint_id} not found")
        
        # Build request
        start_time = time.time()
        
        try:
            # Build URL
            base_url = connector_definition.get("base_url", "")
            path = endpoint.get("path", "")
            url = self._build_url(base_url, path, request.params)
            
            # Build headers
            headers = self._build_headers(request, endpoint)
            
            # Build body
            body = request.body if request.body else None
            
            # Execute HTTP request
            method = endpoint.get("method", "GET").upper()
            
            response = await self._execute_http_request(
                method=method,
                url=url,
                headers=headers,
                body=body,
                timeout=request.timeout
            )
            
            # Record execution time
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Parse response
            response_data = self._parse_response(response)
            
            # Create execution result
            result = ExecutionResult(
                execution_id=execution_id,
                integration_id=integration_id,
                endpoint_id=request.endpoint_id,
                status=ExecutionStatus.SUCCESS,
                request={
                    "method": method,
                    "url": url,
                    "headers": {k: v for k, v in headers.items() if k.lower() not in ["authorization", "api-key"]},
                    "body": body
                },
                response=response_data,
                duration_ms=duration_ms,
                executed_at=datetime.utcnow().isoformat(),
                executed_by=user_id
            )
            
            # Store execution
            self.executions[execution_id] = result
            
            # Update rate limit tracking
            self._record_execution(integration_id)
            
            return result
            
        except httpx.TimeoutException:
            duration_ms = int((time.time() - start_time) * 1000)
            return ExecutionResult(
                execution_id=execution_id,
                integration_id=integration_id,
                endpoint_id=request.endpoint_id,
                status=ExecutionStatus.TIMEOUT,
                request=request.dict(),
                error=f"Request timed out after {request.timeout}s",
                duration_ms=duration_ms,
                executed_at=datetime.utcnow().isoformat(),
                executed_by=user_id
            )
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return ExecutionResult(
                execution_id=execution_id,
                integration_id=integration_id,
                endpoint_id=request.endpoint_id,
                status=ExecutionStatus.FAILED,
                request=request.dict(),
                error=str(e),
                duration_ms=duration_ms,
                executed_at=datetime.utcnow().isoformat(),
                executed_by=user_id
            )
    
    def _find_endpoint(self, connector_definition: Dict[str, Any], endpoint_id: str) -> Optional[Dict[str, Any]]:
        """Find endpoint in connector definition"""
        endpoints = connector_definition.get("endpoints", [])
        for endpoint in endpoints:
            if endpoint.get("id") == endpoint_id:
                return endpoint
        return None
    
    def _build_url(self, base_url: str, path: str, params: Dict[str, Any]) -> str:
        """Build URL with path parameters"""
        url = base_url.rstrip("/") + "/" + path.lstrip("/")
        
        # Replace path parameters
        for key, value in params.items():
            url = url.replace(f"{{{key}}}", str(value))
        
        return url
    
    def _build_headers(self, request: ExecuteIntegrationRequest, endpoint: Dict[str, Any]) -> Dict[str, str]:
        """Build request headers with authentication"""
        headers = {}
        
        # Add default headers
        headers["Content-Type"] = "application/json"
        headers["User-Agent"] = "Brikk-Integration-Engine/1.0"
        
        # Add custom headers from request
        if request.headers:
            headers.update(request.headers)
        
        # Add authentication headers
        if request.auth:
            if request.auth.type == AuthType.API_KEY:
                header_name = request.auth.api_key_header or "Authorization"
                headers[header_name] = request.auth.api_key
            
            elif request.auth.type == AuthType.BEARER_TOKEN:
                headers["Authorization"] = f"Bearer {request.auth.bearer_token}"
            
            elif request.auth.type == AuthType.OAUTH2:
                headers["Authorization"] = f"Bearer {request.auth.oauth2_access_token}"
            
            elif request.auth.type == AuthType.BASIC_AUTH:
                import base64
                credentials = f"{request.auth.basic_username}:{request.auth.basic_password}"
                encoded = base64.b64encode(credentials.encode()).decode()
                headers["Authorization"] = f"Basic {encoded}"
            
            elif request.auth.type == AuthType.CUSTOM:
                if request.auth.custom_headers:
                    headers.update(request.auth.custom_headers)
        
        return headers
    
    async def _execute_http_request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Optional[Dict[str, Any]],
        timeout: int
    ) -> httpx.Response:
        """Execute HTTP request"""
        
        if method == "GET":
            response = await self.client.get(url, headers=headers, timeout=timeout)
        elif method == "POST":
            response = await self.client.post(url, headers=headers, json=body, timeout=timeout)
        elif method == "PUT":
            response = await self.client.put(url, headers=headers, json=body, timeout=timeout)
        elif method == "PATCH":
            response = await self.client.patch(url, headers=headers, json=body, timeout=timeout)
        elif method == "DELETE":
            response = await self.client.delete(url, headers=headers, timeout=timeout)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        response.raise_for_status()
        return response
    
    def _parse_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Parse HTTP response"""
        try:
            return {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response.json() if response.text else None
            }
        except json.JSONDecodeError:
            return {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response.text
            }
    
    def _is_rate_limited(self, integration_id: str) -> bool:
        """Check if integration is rate limited"""
        # Simple rate limiting: max 100 requests per minute
        now = time.time()
        if integration_id not in self.rate_limits:
            self.rate_limits[integration_id] = []
        
        # Remove old timestamps (older than 1 minute)
        self.rate_limits[integration_id] = [
            ts for ts in self.rate_limits[integration_id]
            if now - ts < 60
        ]
        
        # Check if rate limit exceeded
        return len(self.rate_limits[integration_id]) >= 100
    
    def _record_execution(self, integration_id: str):
        """Record execution timestamp for rate limiting"""
        now = time.time()
        if integration_id not in self.rate_limits:
            self.rate_limits[integration_id] = []
        self.rate_limits[integration_id].append(now)
    
    def get_execution(self, execution_id: str) -> Optional[ExecutionResult]:
        """Get execution by ID"""
        return self.executions.get(execution_id)
    
    def list_executions(
        self,
        integration_id: Optional[str] = None,
        user_id: Optional[str] = None,
        status: Optional[ExecutionStatus] = None,
        limit: int = 100
    ) -> List[ExecutionResult]:
        """List executions with filters"""
        results = list(self.executions.values())
        
        if integration_id:
            results = [r for r in results if r.integration_id == integration_id]
        
        if user_id:
            results = [r for r in results if r.executed_by == user_id]
        
        if status:
            results = [r for r in results if r.status == status]
        
        # Sort by executed_at descending
        results.sort(key=lambda x: x.executed_at, reverse=True)
        
        return results[:limit]


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

execution_engine = IntegrationExecutionEngine()
