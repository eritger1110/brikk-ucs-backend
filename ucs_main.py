"""
Universal Connector System (UCS) - Main FastAPI Application

This is the main entry point for the UCS backend API.
It mounts all UCS routes and provides CORS, error handling, and health checks.

Run with: uvicorn ucs_main:app --host 0.0.0.0 --port 8000 --reload
"""

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional, List
from pydantic import BaseModel

# Import UCS services
from integration_registry_api import (
    integration_registry,
    Integration,
    CreateIntegrationRequest,
    UpdateIntegrationRequest,
    IntegrationInstallation
)
from ucs_connector_generation import (
    connector_generation_service,
    OpenAPIGenerationRequest,
    PostmanGenerationRequest,
    URLGenerationRequest,
    TextGenerationRequest,
    SamplesGenerationRequest,
    ConnectorDefinitionFile
)
from integration_execution_engine import (
    execution_engine,
    ExecuteIntegrationRequest,
    ExecutionResult,
    ExecutionStatus
)


# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="Brikk Universal Connector System API",
    description="API for managing integrations and generating connectors",
    version="1.0.0"
)

# ============================================================================
# CORS MIDDLEWARE
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# AUTH HELPER
# ============================================================================

async def get_current_user_id(authorization: Optional[str] = Header(None)) -> str:
    """
    Extract user ID from Authorization header.
    In production, this should validate JWT tokens.
    For MVP, we'll use a demo user ID.
    """
    # TODO: Implement proper JWT validation
    # For now, return demo user ID
    return "demo-user"


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ucs-api",
        "version": "1.0.0"
    }


# ============================================================================
# INTEGRATION REGISTRY ROUTES
# ============================================================================

@app.get("/api/v1/integrations", response_model=List[Integration])
async def list_integrations(
    category: Optional[str] = None,
    search: Optional[str] = None,
    status: Optional[str] = None,
    created_by: Optional[str] = None,
    user_id: str = Depends(get_current_user_id)
):
    """
    List all integrations with optional filters
    
    Query parameters:
    - category: Filter by category (e.g., "CRM", "ERP")
    - search: Search in name and description
    - status: Filter by status ("published", "draft", "deprecated")
    - created_by: Filter by creator user ID
    """
    integrations = integration_registry.list_integrations(
        category=category,
        search=search,
        status=status,
        created_by=created_by
    )
    
    # Add is_installed flag for current user
    for integration in integrations:
        integration.metadata = {
            "is_installed": integration_registry.is_installed(integration.id, user_id)
        }
    
    return integrations


@app.get("/api/v1/integrations/{integration_id}", response_model=Integration)
async def get_integration(
    integration_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get integration details by ID"""
    integration = integration_registry.get_integration(integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    # Add is_installed flag
    integration.metadata = {
        "is_installed": integration_registry.is_installed(integration_id, user_id)
    }
    
    return integration


@app.post("/api/v1/integrations", response_model=Integration)
async def create_integration(
    request: CreateIntegrationRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Create a new integration"""
    integration = integration_registry.create_integration(request, user_id)
    return integration


@app.put("/api/v1/integrations/{integration_id}", response_model=Integration)
async def update_integration(
    integration_id: str,
    request: UpdateIntegrationRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Update an existing integration"""
    integration = integration_registry.update_integration(integration_id, request, user_id)
    return integration


@app.delete("/api/v1/integrations/{integration_id}")
async def delete_integration(
    integration_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Delete an integration"""
    integration_registry.delete_integration(integration_id, user_id)
    return {"message": "Integration deleted successfully"}


@app.post("/api/v1/integrations/{integration_id}/install", response_model=IntegrationInstallation)
async def install_integration(
    integration_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Install an integration for the current user"""
    installation = integration_registry.install_integration(integration_id, user_id)
    return installation


@app.delete("/api/v1/integrations/{integration_id}/install")
async def uninstall_integration(
    integration_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Uninstall an integration for the current user"""
    integration_registry.uninstall_integration(integration_id, user_id)
    return {"message": "Integration uninstalled successfully"}


@app.get("/api/v1/integrations/me/installations", response_model=List[IntegrationInstallation])
async def get_my_installations(user_id: str = Depends(get_current_user_id)):
    """Get all installations for the current user"""
    return integration_registry.get_user_installations(user_id)


@app.get("/api/v1/integrations/categories")
async def get_categories():
    """Get all integration categories with counts"""
    return integration_registry.get_categories()


# ============================================================================
# CONNECTOR GENERATION ROUTES
# ============================================================================

@app.post("/api/v1/connectors/generate/openapi", response_model=ConnectorDefinitionFile)
async def generate_from_openapi(
    request: OpenAPIGenerationRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Generate connector from OpenAPI/Swagger specification
    
    Request body should include:
    - integration_name: Name of the integration
    - integration_category: Category (e.g., "CRM", "ERP")
    - integration_description: Description
    - openapi_spec: OpenAPI 3.0 specification (JSON object)
    """
    cdf = await connector_generation_service.generate_from_openapi(request)
    return cdf


@app.post("/api/v1/connectors/generate/postman", response_model=ConnectorDefinitionFile)
async def generate_from_postman(
    request: PostmanGenerationRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Generate connector from Postman collection
    
    Request body should include:
    - integration_name: Name of the integration
    - integration_category: Category
    - integration_description: Description
    - postman_collection: Postman Collection v2.1 (JSON object)
    """
    cdf = await connector_generation_service.generate_from_postman(request)
    return cdf


@app.post("/api/v1/connectors/generate/url", response_model=ConnectorDefinitionFile)
async def generate_from_url(
    request: URLGenerationRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Generate connector by scraping API documentation URL
    
    Request body should include:
    - integration_name: Name of the integration
    - integration_category: Category
    - integration_description: Description
    - documentation_url: URL to API documentation
    """
    cdf = await connector_generation_service.generate_from_url(request)
    return cdf


@app.post("/api/v1/connectors/generate/text", response_model=ConnectorDefinitionFile)
async def generate_from_text(
    request: TextGenerationRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Generate connector from raw text documentation
    
    Request body should include:
    - integration_name: Name of the integration
    - integration_category: Category
    - integration_description: Description
    - documentation_text: Raw text documentation
    """
    cdf = await connector_generation_service.generate_from_text(request)
    return cdf


@app.post("/api/v1/connectors/generate/samples", response_model=ConnectorDefinitionFile)
async def generate_from_samples(
    request: SamplesGenerationRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Generate connector from sample CURL requests
    
    Request body should include:
    - integration_name: Name of the integration
    - integration_category: Category
    - integration_description: Description
    - sample_requests: List of CURL commands
    """
    cdf = await connector_generation_service.generate_from_samples(request)
    return cdf


@app.post("/api/v1/connectors/save")
async def save_connector(
    connector: ConnectorDefinitionFile,
    user_id: str = Depends(get_current_user_id)
):
    """
    Save a generated connector to the integration registry
    
    This creates a new integration from the CDF.
    """
    # Create integration from CDF
    create_request = CreateIntegrationRequest(
        name=connector.name,
        category=connector.metadata.get("category", "Other"),
        description=connector.description,
        icon="🔌",
        base_url=connector.base_url,
        connector_definition=connector.dict()
    )
    
    integration = integration_registry.create_integration(create_request, user_id)
    return {
        "message": "Connector saved successfully",
        "integration_id": integration.id
    }


# ============================================================================
# INTEGRATION EXECUTION ROUTES
# ============================================================================

@app.post("/api/v1/integrations/{integration_id}/execute", response_model=ExecutionResult)
async def execute_integration(
    integration_id: str,
    request: ExecuteIntegrationRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Execute an integration endpoint
    
    This is the core endpoint that agents and workflows use to call integration APIs.
    
    Request body should include:
    - endpoint_id: ID of the endpoint to execute
    - params: URL/path parameters
    - body: Request body (for POST/PUT/PATCH)
    - headers: Custom headers
    - auth: Authentication configuration
    - timeout: Request timeout in seconds
    """
    # Get integration
    integration = integration_registry.get_integration(integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    # Check if user has installed this integration
    installations = integration_registry.get_user_installations(user_id)
    if integration_id not in [i.integration_id for i in installations]:
        raise HTTPException(status_code=403, detail="Integration not installed. Please install it first.")
    
    # Execute integration
    result = await execution_engine.execute(
        integration_id=integration_id,
        request=request,
        user_id=user_id,
        connector_definition=integration.connector_definition
    )
    
    return result


@app.get("/api/v1/integrations/{integration_id}/executions")
async def list_integration_executions(
    integration_id: str,
    user_id: str = Depends(get_current_user_id),
    status: Optional[ExecutionStatus] = None,
    limit: int = 100
):
    """
    List execution history for an integration
    """
    executions = execution_engine.list_executions(
        integration_id=integration_id,
        user_id=user_id,
        status=status,
        limit=limit
    )
    return executions


@app.get("/api/v1/executions/{execution_id}", response_model=ExecutionResult)
async def get_execution(
    execution_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Get execution details by ID
    """
    execution = execution_engine.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    # Check if user owns this execution
    if execution.executed_by != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return execution


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )


# ============================================================================
# STARTUP/SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    print("🚀 Brikk UCS API starting up...")
    print(f"📦 Loaded {len(integration_registry.integrations)} integrations")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    print("👋 Brikk UCS API shutting down...")


# ============================================================================
# MAIN (for local development)
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
