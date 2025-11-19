"""
LLM Service for intelligent connector generation
Uses OpenAI GPT-4 to parse API documentation and generate connector definitions
"""

import os
import json
from typing import Dict, Any, Optional
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

CONNECTOR_GENERATION_PROMPT = """You are an expert API integration engineer. Your task is to analyze API documentation and generate a complete connector definition in JSON format.

The connector definition must follow this exact structure:

{
  "name": "API Name",
  "description": "Brief description of what this API does",
  "base_url": "https://api.example.com",
  "version": "1.0.0",
  "auth": {
    "type": "oauth2" | "api_key" | "bearer" | "basic" | "none",
    "config": {
      // Auth-specific configuration
    }
  },
  "endpoints": [
    {
      "id": "unique_endpoint_id",
      "name": "Human-readable endpoint name",
      "description": "What this endpoint does",
      "method": "GET" | "POST" | "PUT" | "DELETE" | "PATCH",
      "path": "/api/v1/resource",
      "parameters": [
        {
          "name": "param_name",
          "type": "string" | "number" | "boolean" | "object" | "array",
          "in": "query" | "path" | "header" | "body",
          "required": true | false,
          "description": "Parameter description"
        }
      ],
      "response": {
        "type": "object",
        "properties": {
          // Response schema
        }
      }
    }
  ],
  "rate_limits": {
    "requests_per_second": 10,
    "requests_per_minute": 100,
    "requests_per_hour": 1000
  },
  "error_codes": {
    "400": "Bad Request",
    "401": "Unauthorized",
    "403": "Forbidden",
    "404": "Not Found",
    "429": "Too Many Requests",
    "500": "Internal Server Error"
  }
}

Guidelines:
1. Extract ALL available endpoints from the documentation
2. Identify the correct authentication method
3. Parse all parameters with correct types and locations
4. Include response schemas when available
5. Identify rate limits if mentioned
6. Be thorough but concise in descriptions
7. Use consistent naming conventions (snake_case for IDs, Title Case for names)
8. If information is missing, make reasonable assumptions based on API best practices

Return ONLY the JSON object, no additional text or markdown formatting."""


async def generate_connector_from_text(
    documentation_text: str,
    integration_name: str,
    integration_description: str,
) -> Dict[str, Any]:
    """
    Generate a connector definition from raw API documentation text using GPT-4
    
    Args:
        documentation_text: Raw API documentation text
        integration_name: Name of the integration
        integration_description: Brief description of the integration
        
    Returns:
        Complete connector definition as a dictionary
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": CONNECTOR_GENERATION_PROMPT},
                {
                    "role": "user",
                    "content": f"""Integration Name: {integration_name}
Integration Description: {integration_description}

API Documentation:
{documentation_text}

Generate a complete connector definition for this API."""
                }
            ],
            temperature=0.1,  # Low temperature for consistent, factual output
            max_tokens=4000,
        )
        
        # Extract JSON from response
        content = response.choices[0].message.content
        
        # Try to parse as JSON
        try:
            connector_def = json.loads(content)
        except json.JSONDecodeError:
            # If response includes markdown code blocks, extract JSON
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
                connector_def = json.loads(json_str)
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
                connector_def = json.loads(json_str)
            else:
                raise ValueError("Failed to extract JSON from LLM response")
        
        # Ensure required fields are present
        if "name" not in connector_def:
            connector_def["name"] = integration_name
        if "description" not in connector_def:
            connector_def["description"] = integration_description
        if "version" not in connector_def:
            connector_def["version"] = "1.0.0"
            
        return connector_def
        
    except Exception as e:
        print(f"LLM generation failed: {str(e)}")
        raise Exception(f"Failed to generate connector: {str(e)}")


async def generate_connector_from_url(
    documentation_url: str,
    integration_name: str,
    integration_description: str,
) -> Dict[str, Any]:
    """
    Generate a connector definition from a documentation URL using GPT-4
    
    First scrapes the URL content, then uses LLM to parse it
    
    Args:
        documentation_url: URL to API documentation
        integration_name: Name of the integration
        integration_description: Brief description of the integration
        
    Returns:
        Complete connector definition as a dictionary
    """
    import httpx
    from bs4 import BeautifulSoup
    
    try:
        # Scrape the documentation page
        async with httpx.AsyncClient() as client_http:
            response = await client_http.get(documentation_url, timeout=30.0)
            response.raise_for_status()
            
        # Parse HTML and extract text
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
            
        # Get text
        text = soup.get_text()
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        # Limit text length to avoid token limits
        max_chars = 15000
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[Documentation truncated...]"
        
        # Use LLM to generate connector from scraped text
        return await generate_connector_from_text(
            text,
            integration_name,
            integration_description
        )
        
    except Exception as e:
        print(f"URL scraping failed: {str(e)}")
        raise Exception(f"Failed to scrape and generate connector: {str(e)}")


async def enhance_connector_definition(
    connector_def: Dict[str, Any],
    additional_context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Enhance an existing connector definition with additional details using GPT-4
    
    Args:
        connector_def: Existing connector definition
        additional_context: Optional additional context or requirements
        
    Returns:
        Enhanced connector definition
    """
    try:
        prompt = f"""You are an API integration expert. Review and enhance this connector definition.

Current Connector Definition:
{json.dumps(connector_def, indent=2)}

{f"Additional Context: {additional_context}" if additional_context else ""}

Tasks:
1. Add missing endpoint descriptions
2. Improve parameter descriptions
3. Add response schema examples
4. Suggest additional useful endpoints if obvious from the API pattern
5. Ensure authentication configuration is complete
6. Add reasonable rate limits if missing

Return the enhanced connector definition as JSON."""

        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are an API integration expert."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=4000,
        )
        
        content = response.choices[0].message.content
        
        # Parse JSON
        try:
            enhanced_def = json.loads(content)
        except json.JSONDecodeError:
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
                enhanced_def = json.loads(json_str)
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
                enhanced_def = json.loads(json_str)
            else:
                # If parsing fails, return original
                return connector_def
                
        return enhanced_def
        
    except Exception as e:
        print(f"Enhancement failed: {str(e)}")
        # Return original if enhancement fails
        return connector_def


async def validate_connector_definition(connector_def: Dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Validate a connector definition for completeness and correctness
    
    Args:
        connector_def: Connector definition to validate
        
    Returns:
        Tuple of (is_valid, list of error messages)
    """
    errors = []
    
    # Check required fields
    required_fields = ["name", "description", "base_url", "version", "auth", "endpoints"]
    for field in required_fields:
        if field not in connector_def:
            errors.append(f"Missing required field: {field}")
    
    # Validate base_url
    if "base_url" in connector_def:
        base_url = connector_def["base_url"]
        if not base_url.startswith("http://") and not base_url.startswith("https://"):
            errors.append("base_url must start with http:// or https://")
    
    # Validate auth
    if "auth" in connector_def:
        auth = connector_def["auth"]
        if "type" not in auth:
            errors.append("auth.type is required")
        elif auth["type"] not in ["oauth2", "api_key", "bearer", "basic", "none"]:
            errors.append(f"Invalid auth type: {auth['type']}")
    
    # Validate endpoints
    if "endpoints" in connector_def:
        endpoints = connector_def["endpoints"]
        if not isinstance(endpoints, list):
            errors.append("endpoints must be an array")
        elif len(endpoints) == 0:
            errors.append("At least one endpoint is required")
        else:
            for i, endpoint in enumerate(endpoints):
                if "method" not in endpoint:
                    errors.append(f"Endpoint {i}: missing method")
                elif endpoint["method"] not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                    errors.append(f"Endpoint {i}: invalid method {endpoint['method']}")
                    
                if "path" not in endpoint:
                    errors.append(f"Endpoint {i}: missing path")
    
    return len(errors) == 0, errors
