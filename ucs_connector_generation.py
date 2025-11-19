"""
Universal Connector System (UCS) - Connector Generation Service (CGS)

This service generates integration connectors from various input formats:
- OpenAPI/Swagger specifications
- Postman collections  
- API documentation URLs
- Raw text documentation
- Sample CURL requests

Output: Connector Definition File (CDF) in JSON format
"""

import json
import re
import os
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pydantic import BaseModel, Field
import httpx
from bs4 import BeautifulSoup

# Try to import LLM service if OpenAI key is available
USE_LLM = os.environ.get("OPENAI_API_KEY") is not None
if USE_LLM:
    try:
        from llm_service import generate_connector_from_text, generate_connector_from_url as llm_generate_from_url
    except ImportError:
        USE_LLM = False


# ============================================================================
# MODELS
# ============================================================================

class EndpointDefinition(BaseModel):
    """Definition of a single API endpoint"""
    id: str
    name: str
    description: str
    method: str  # GET, POST, PUT, DELETE, PATCH
    path: str
    parameters: List[Dict[str, Any]] = Field(default_factory=list)
    request_body: Optional[Dict[str, Any]] = None
    responses: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    auth_required: bool = True
    rate_limit: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class AuthMethod(BaseModel):
    """Authentication method configuration"""
    type: str  # oauth2, api_key, basic, bearer, custom
    config: Dict[str, Any]


class ConnectorDefinitionFile(BaseModel):
    """Complete Connector Definition File (CDF)"""
    id: str
    name: str
    version: str
    description: str
    base_url: str
    auth_methods: List[AuthMethod]
    endpoints: List[EndpointDefinition]
    rate_limits: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str


class GenerationRequest(BaseModel):
    """Request to generate a connector"""
    integration_name: str
    integration_category: str
    integration_description: str


class OpenAPIGenerationRequest(GenerationRequest):
    """Generate from OpenAPI/Swagger file"""
    openapi_spec: Dict[str, Any]


class PostmanGenerationRequest(GenerationRequest):
    """Generate from Postman collection"""
    postman_collection: Dict[str, Any]


class URLGenerationRequest(GenerationRequest):
    """Generate from API documentation URL"""
    documentation_url: str


class TextGenerationRequest(GenerationRequest):
    """Generate from raw text documentation"""
    documentation_text: str


class SamplesGenerationRequest(GenerationRequest):
    """Generate from sample CURL requests"""
    sample_requests: List[str]


# ============================================================================
# CONNECTOR GENERATION SERVICE
# ============================================================================

class ConnectorGenerationService:
    """Service for generating integration connectors from various sources"""
    
    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    async def generate_from_openapi(self, request: OpenAPIGenerationRequest) -> ConnectorDefinitionFile:
        """Generate connector from OpenAPI/Swagger specification"""
        spec = request.openapi_spec
        
        # Extract base information
        info = spec.get("info", {})
        servers = spec.get("servers", [])
        base_url = servers[0]["url"] if servers else "https://api.example.com"
        
        # Parse authentication methods
        auth_methods = self._parse_openapi_auth(spec.get("components", {}).get("securitySchemes", {}))
        
        # Parse endpoints
        endpoints = []
        paths = spec.get("paths", {})
        
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.upper() not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                    continue
                
                endpoint = self._parse_openapi_endpoint(
                    path=path,
                    method=method.upper(),
                    operation=operation
                )
                endpoints.append(endpoint)
        
        # Create CDF
        now = datetime.utcnow().isoformat()
        cdf = ConnectorDefinitionFile(
            id=self._generate_id(request.integration_name),
            name=request.integration_name,
            version="1.0.0",
            description=request.integration_description or info.get("description", ""),
            base_url=base_url,
            auth_methods=auth_methods,
            endpoints=endpoints,
            metadata={
                "source": "openapi",
                "openapi_version": spec.get("openapi", "3.0.0"),
                "category": request.integration_category
            },
            created_at=now,
            updated_at=now
        )
        
        return cdf
    
    async def generate_from_postman(self, request: PostmanGenerationRequest) -> ConnectorDefinitionFile:
        """Generate connector from Postman collection"""
        collection = request.postman_collection
        info = collection.get("info", {})
        
        # Extract base URL from first request or use default
        base_url = "https://api.example.com"
        items = collection.get("item", [])
        if items and isinstance(items[0], dict):
            first_request = items[0].get("request", {})
            if isinstance(first_request, dict):
                url = first_request.get("url", {})
                if isinstance(url, dict):
                    protocol = url.get("protocol", "https")
                    host = ".".join(url.get("host", ["api", "example", "com"]))
                    base_url = f"{protocol}://{host}"
        
        # Parse authentication
        auth_methods = self._parse_postman_auth(collection.get("auth", {}))
        
        # Parse endpoints from items
        endpoints: List[EndpointDefinition] = []
        self._parse_postman_items(items, endpoints, "")
        
        # Create CDF
        now = datetime.utcnow().isoformat()
        cdf = ConnectorDefinitionFile(
            id=self._generate_id(request.integration_name),
            name=request.integration_name,
            version="1.0.0",
            description=request.integration_description or info.get("description", ""),
            base_url=base_url,
            auth_methods=auth_methods,
            endpoints=endpoints,
            metadata={
                "source": "postman",
                "collection_name": info.get("name", ""),
                "category": request.integration_category
            },
            created_at=now,
            updated_at=now
        )
        
        return cdf
    
    async def generate_from_url(self, request: URLGenerationRequest) -> ConnectorDefinitionFile:
        """Generate connector by scraping API documentation URL"""
        # Fetch documentation page
        response = await self.http_client.get(request.documentation_url)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract base URL (heuristic: look for code blocks with URLs)
        base_url = self._extract_base_url(soup) or "https://api.example.com"
        
        # Extract endpoints (heuristic: look for HTTP methods + paths)
        endpoints = self._extract_endpoints_from_html(soup)
        
        # Default auth (assume API key for now)
        auth_methods = [
            AuthMethod(
                type="api_key",
                config={
                    "header_name": "Authorization",
                    "prefix": "Bearer"
                }
            )
        ]
        
        # Create CDF
        now = datetime.utcnow().isoformat()
        cdf = ConnectorDefinitionFile(
            id=self._generate_id(request.integration_name),
            name=request.integration_name,
            version="1.0.0",
            description=request.integration_description,
            base_url=base_url,
            auth_methods=auth_methods,
            endpoints=endpoints,
            metadata={
                "source": "url",
                "documentation_url": request.documentation_url,
                "category": request.integration_category
            },
            created_at=now,
            updated_at=now
        )
        
        return cdf
    
    async def generate_from_text(self, request: TextGenerationRequest) -> ConnectorDefinitionFile:
        """Generate connector from raw text documentation using LLM or pattern matching"""
        text = request.documentation_text
        
        # Try LLM-based generation first if available
        if USE_LLM:
            try:
                llm_result = await generate_connector_from_text(
                    text,
                    request.integration_name,
                    request.integration_description
                )
                
                # Convert LLM result to CDF format
                now = datetime.utcnow().isoformat()
                
                # Parse auth methods
                auth_methods = []
                if "auth" in llm_result:
                    auth_config = llm_result["auth"]
                    auth_methods.append(AuthMethod(
                        type=auth_config.get("type", "api_key"),
                        config=auth_config.get("config", {})
                    ))
                else:
                    auth_methods.append(AuthMethod(type="api_key", config={"header_name": "Authorization"}))
                
                # Parse endpoints
                endpoints = []
                for ep in llm_result.get("endpoints", []):
                    endpoints.append(EndpointDefinition(
                        id=ep.get("id", ""),
                        name=ep.get("name", ""),
                        description=ep.get("description", ""),
                        method=ep.get("method", "GET"),
                        path=ep.get("path", "/"),
                        parameters=ep.get("parameters", []),
                        request_body=ep.get("request_body"),
                        responses=ep.get("responses", {}),
                        tags=ep.get("tags", [])
                    ))
                
                cdf = ConnectorDefinitionFile(
                    id=self._generate_id(request.integration_name),
                    name=llm_result.get("name", request.integration_name),
                    version=llm_result.get("version", "1.0.0"),
                    description=llm_result.get("description", request.integration_description),
                    base_url=llm_result.get("base_url", "https://api.example.com"),
                    auth_methods=auth_methods,
                    endpoints=endpoints,
                    rate_limits=llm_result.get("rate_limits", {}),
                    metadata={
                        "source": "text",
                        "category": request.integration_category,
                        "generation_method": "llm",
                        "model": "gpt-4-turbo-preview"
                    },
                    created_at=now,
                    updated_at=now
                )
                
                return cdf
                
            except Exception as e:
                print(f"LLM generation failed, falling back to pattern matching: {str(e)}")
        
        # Fallback to pattern matching
        base_url_match = re.search(r'https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
        base_url = base_url_match.group(0) if base_url_match else "https://api.example.com"
        
        endpoints = self._extract_endpoints_from_text(text)
        
        auth_methods = [
            AuthMethod(
                type="api_key",
                config={
                    "header_name": "Authorization",
                    "prefix": "Bearer"
                }
            )
        ]
        
        now = datetime.utcnow().isoformat()
        cdf = ConnectorDefinitionFile(
            id=self._generate_id(request.integration_name),
            name=request.integration_name,
            version="1.0.0",
            description=request.integration_description,
            base_url=base_url,
            auth_methods=auth_methods,
            endpoints=endpoints,
            metadata={
                "source": "text",
                "category": request.integration_category,
                "generation_method": "pattern_matching",
                "note": "Generated using pattern matching. Consider manual review."
            },
            created_at=now,
            updated_at=now
        )
        
        return cdf
    
    async def generate_from_samples(self, request: SamplesGenerationRequest) -> ConnectorDefinitionFile:
        """Generate connector from sample CURL requests"""
        endpoints = []
        base_urls = set()
        
        for sample in request.sample_requests:
            endpoint, base_url = self._parse_curl_command(sample)
            if endpoint:
                endpoints.append(endpoint)
            if base_url:
                base_urls.add(base_url)
        
        # Use most common base URL
        base_url = list(base_urls)[0] if base_urls else "https://api.example.com"
        
        # Default auth
        auth_methods = [
            AuthMethod(
                type="api_key",
                config={
                    "header_name": "Authorization",
                    "prefix": "Bearer"
                }
            )
        ]
        
        # Create CDF
        now = datetime.utcnow().isoformat()
        cdf = ConnectorDefinitionFile(
            id=self._generate_id(request.integration_name),
            name=request.integration_name,
            version="1.0.0",
            description=request.integration_description,
            base_url=base_url,
            auth_methods=auth_methods,
            endpoints=endpoints,
            metadata={
                "source": "samples",
                "sample_count": len(request.sample_requests),
                "category": request.integration_category
            },
            created_at=now,
            updated_at=now
        )
        
        return cdf
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _generate_id(self, name: str) -> str:
        """Generate unique ID from integration name"""
        return re.sub(r'[^a-z0-9-]', '-', name.lower()).strip('-')
    
    def _parse_openapi_auth(self, security_schemes: Dict) -> List[AuthMethod]:
        """Parse OpenAPI security schemes into auth methods"""
        auth_methods = []
        
        for scheme_name, scheme in security_schemes.items():
            scheme_type = scheme.get("type", "")
            
            if scheme_type == "oauth2":
                flows = scheme.get("flows", {})
                auth_methods.append(AuthMethod(
                    type="oauth2",
                    config={
                        "flows": flows,
                        "scheme_name": scheme_name
                    }
                ))
            elif scheme_type == "apiKey":
                auth_methods.append(AuthMethod(
                    type="api_key",
                    config={
                        "header_name": scheme.get("name", "Authorization"),
                        "in": scheme.get("in", "header")
                    }
                ))
            elif scheme_type == "http":
                auth_methods.append(AuthMethod(
                    type=scheme.get("scheme", "bearer"),
                    config={
                        "scheme_name": scheme_name
                    }
                ))
        
        return auth_methods or [AuthMethod(type="api_key", config={"header_name": "Authorization"})]
    
    def _parse_openapi_endpoint(self, path: str, method: str, operation: Dict) -> EndpointDefinition:
        """Parse OpenAPI operation into endpoint definition"""
        endpoint_id = operation.get("operationId", f"{method.lower()}{path.replace('/', '_')}")
        
        # Parse parameters
        parameters = []
        for param in operation.get("parameters", []):
            parameters.append({
                "name": param.get("name"),
                "in": param.get("in"),
                "required": param.get("required", False),
                "schema": param.get("schema", {}),
                "description": param.get("description", "")
            })
        
        # Parse request body
        request_body = None
        if "requestBody" in operation:
            content = operation["requestBody"].get("content", {})
            if "application/json" in content:
                request_body = content["application/json"].get("schema", {})
        
        # Parse responses
        responses = {}
        for status_code, response in operation.get("responses", {}).items():
            content = response.get("content", {})
            schema = None
            if "application/json" in content:
                schema = content["application/json"].get("schema", {})
            
            responses[status_code] = {
                "description": response.get("description", ""),
                "schema": schema
            }
        
        return EndpointDefinition(
            id=endpoint_id,
            name=operation.get("summary", endpoint_id),
            description=operation.get("description", ""),
            method=method,
            path=path,
            parameters=parameters,
            request_body=request_body,
            responses=responses,
            tags=operation.get("tags", [])
        )
    
    def _parse_postman_auth(self, auth: Dict) -> List[AuthMethod]:
        """Parse Postman auth into auth methods"""
        if not auth:
            return [AuthMethod(type="api_key", config={"header_name": "Authorization"})]
        
        auth_type = auth.get("type", "")
        
        if auth_type == "bearer":
            return [AuthMethod(type="bearer", config={"token_field": "token"})]
        elif auth_type == "apikey":
            return [AuthMethod(type="api_key", config={
                "header_name": auth.get("key", "Authorization"),
                "value": auth.get("value", "")
            })]
        elif auth_type == "oauth2":
            return [AuthMethod(type="oauth2", config=auth.get("oauth2", {}))]
        
        return [AuthMethod(type="api_key", config={"header_name": "Authorization"})]
    
    def _parse_postman_items(self, items: List, endpoints: List[EndpointDefinition], parent_path: str):
        """Recursively parse Postman collection items"""
        for item in items:
            if "item" in item:
                # Folder - recurse
                folder_name = item.get("name", "")
                self._parse_postman_items(item["item"], endpoints, f"{parent_path}/{folder_name}")
            elif "request" in item:
                # Request - parse endpoint
                request = item["request"]
                if isinstance(request, dict):
                    endpoint = self._parse_postman_request(request, item.get("name", ""), parent_path)
                    if endpoint:
                        endpoints.append(endpoint)
    
    def _parse_postman_request(self, request: Dict, name: str, parent_path: str) -> Optional[EndpointDefinition]:
        """Parse Postman request into endpoint definition"""
        method = request.get("method", "GET")
        url = request.get("url", {})
        
        if isinstance(url, str):
            path = url
        elif isinstance(url, dict):
            path = "/" + "/".join(url.get("path", []))
        else:
            return None
        
        # Parse headers as parameters
        parameters = []
        for header in request.get("header", []):
            if header.get("key") not in ["Authorization", "Content-Type"]:
                parameters.append({
                    "name": header.get("key"),
                    "in": "header",
                    "required": False,
                    "description": header.get("description", "")
                })
        
        # Parse query parameters
        if isinstance(url, dict):
            for query in url.get("query", []):
                parameters.append({
                    "name": query.get("key"),
                    "in": "query",
                    "required": False,
                    "description": query.get("description", "")
                })
        
        # Parse body
        request_body = None
        body = request.get("body", {})
        if body.get("mode") == "raw":
            try:
                request_body = json.loads(body.get("raw", "{}"))
            except:
                pass
        
        endpoint_id = re.sub(r'[^a-z0-9_]', '_', f"{method.lower()}_{name}".lower())
        
        return EndpointDefinition(
            id=endpoint_id,
            name=name,
            description=request.get("description", ""),
            method=method,
            path=path,
            parameters=parameters,
            request_body=request_body,
            responses={"200": {"description": "Success"}},
            tags=[parent_path.strip("/")] if parent_path else []
        )
    
    def _extract_base_url(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract base URL from HTML documentation"""
        # Look for code blocks with URLs
        code_blocks = soup.find_all(['code', 'pre'])
        for block in code_blocks:
            text = block.get_text()
            match = re.search(r'https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
            if match:
                url = match.group(0)
                # Remove path if present
                base_url_match = re.match(r'https?://[^/]+', url)
                if base_url_match:
                    return base_url_match.group(0)
        return None
    
    def _extract_endpoints_from_html(self, soup: BeautifulSoup) -> List[EndpointDefinition]:
        """Extract endpoints from HTML documentation using heuristics"""
        endpoints = []
        
        # Look for HTTP method + path patterns
        code_blocks = soup.find_all(['code', 'pre'])
        for block in code_blocks:
            text = block.get_text()
            # Pattern: GET /api/users
            matches = re.findall(r'(GET|POST|PUT|DELETE|PATCH)\s+(/[^\s]+)', text)
            for method, path in matches:
                endpoint_id = re.sub(r'[^a-z0-9_]', '_', f"{method.lower()}{path}".lower())
                endpoints.append(EndpointDefinition(
                    id=endpoint_id,
                    name=f"{method} {path}",
                    description="",
                    method=method,
                    path=path,
                    responses={"200": {"description": "Success"}}
                ))
        
        return endpoints[:50]  # Limit to 50 endpoints
    
    def _extract_endpoints_from_text(self, text: str) -> List[EndpointDefinition]:
        """Extract endpoints from raw text using pattern matching"""
        endpoints = []
        
        # Pattern: GET /api/users - Description
        matches = re.findall(r'(GET|POST|PUT|DELETE|PATCH)\s+(/[^\s]+)(?:\s*-\s*(.+))?', text)
        for method, path, description in matches:
            endpoint_id = re.sub(r'[^a-z0-9_]', '_', f"{method.lower()}{path}".lower())
            endpoints.append(EndpointDefinition(
                id=endpoint_id,
                name=f"{method} {path}",
                description=description.strip() if description else "",
                method=method,
                path=path,
                responses={"200": {"description": "Success"}}
            ))
        
        return endpoints[:50]  # Limit to 50 endpoints
    
    def _parse_curl_command(self, curl: str) -> Tuple[Optional[EndpointDefinition], Optional[str]]:
        """Parse CURL command into endpoint definition"""
        # Extract URL
        url_match = re.search(r'curl\s+(?:-X\s+\w+\s+)?["\']?(https?://[^\s"\']+)', curl)
        if not url_match:
            return None, None
        
        full_url = url_match.group(1)
        
        # Extract base URL
        base_url_match = re.match(r'(https?://[^/]+)', full_url)
        base_url = base_url_match.group(1) if base_url_match else None
        
        # Extract path
        path = full_url.replace(base_url, "") if base_url else full_url
        if not path.startswith("/"):
            path = "/" + path
        
        # Extract method
        method_match = re.search(r'-X\s+(GET|POST|PUT|DELETE|PATCH)', curl)
        method = method_match.group(1) if method_match else "GET"
        
        # Extract headers as parameters
        parameters = []
        header_matches = re.findall(r'-H\s+["\']([^:]+):\s*([^"\']+)["\']', curl)
        for header_name, header_value in header_matches:
            if header_name not in ["Authorization", "Content-Type"]:
                parameters.append({
                    "name": header_name,
                    "in": "header",
                    "required": False,
                    "example": header_value
                })
        
        # Extract body
        request_body = None
        body_match = re.search(r'-d\s+["\'](.+)["\']', curl)
        if body_match:
            try:
                request_body = json.loads(body_match.group(1))
            except:
                pass
        
        endpoint_id = re.sub(r'[^a-z0-9_]', '_', f"{method.lower()}{path}".lower())
        
        endpoint = EndpointDefinition(
            id=endpoint_id,
            name=f"{method} {path}",
            description="",
            method=method,
            path=path,
            parameters=parameters,
            request_body=request_body,
            responses={"200": {"description": "Success"}}
        )
        
        return endpoint, base_url


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

connector_generation_service = ConnectorGenerationService()
