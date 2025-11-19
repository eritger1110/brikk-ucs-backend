"""
Integration Registry API

CRUD API for managing integrations in the Universal Connector System.
Uses in-memory storage for MVP (can be replaced with database later).

Endpoints:
- GET /api/v1/integrations - List all integrations
- GET /api/v1/integrations/{id} - Get integration details
- POST /api/v1/integrations - Create integration
- PUT /api/v1/integrations/{id} - Update integration
- DELETE /api/v1/integrations/{id} - Delete integration
- POST /api/v1/integrations/{id}/install - Install integration
- DELETE /api/v1/integrations/{id}/install - Uninstall integration
- GET /api/v1/integrations/categories - List categories
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from fastapi import HTTPException


# ============================================================================
# MODELS
# ============================================================================

class Integration(BaseModel):
    """Integration model"""
    id: str
    name: str
    version: str
    category: str
    description: str
    icon: str
    base_url: str
    status: str  # published, draft, deprecated
    health_status: str  # healthy, degraded, failed
    install_count: int = 0
    rating: float = 0.0
    rating_count: int = 0
    tags: List[str] = Field(default_factory=list)
    created_by_user_id: str
    created_at: str
    updated_at: str
    last_health_check: Optional[str] = None
    connector_definition: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IntegrationInstallation(BaseModel):
    """Installation record"""
    integration_id: str
    user_id: str
    installed_at: str
    version: str


class CreateIntegrationRequest(BaseModel):
    """Request to create integration"""
    name: str
    category: str
    description: str
    icon: str = "🔌"
    base_url: str
    connector_definition: Dict[str, Any]


class UpdateIntegrationRequest(BaseModel):
    """Request to update integration"""
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    base_url: Optional[str] = None
    status: Optional[str] = None
    connector_definition: Optional[Dict[str, Any]] = None


# ============================================================================
# IN-MEMORY STORAGE
# ============================================================================

class IntegrationRegistry:
    """In-memory storage for integrations"""
    
    def __init__(self):
        self.integrations: Dict[str, Integration] = {}
        self.installations: Dict[str, List[IntegrationInstallation]] = {}  # user_id -> installations
        self._seed_data()
    
    def _seed_data(self):
        """Seed with 56 integrations from JSON file"""
        import json
        import os
        
        # Load integrations from JSON file
        json_path = os.path.join(os.path.dirname(__file__), 'integrations_seed.json')
        
        if os.path.exists(json_path):
            with open(json_path, 'r') as f:
                sample_integrations = json.load(f)
        else:
            # Fallback to minimal seed data if file doesn't exist
            now = datetime.utcnow().isoformat()
            sample_integrations = [
                {
                    "id": "shopify",
                    "name": "Shopify",
                    "version": "2.1.0",
                    "category": "E-commerce",
                    "description": "E-commerce platform",
                    "icon": "🛒",
                    "base_url": "https://api.shopify.com",
                    "status": "published",
                    "health_status": "healthy",
                    "install_count": 15400,
                    "rating": 4.8,
                    "rating_count": 892,
                    "tags": ["ecommerce"],
                    "created_by_user_id": "brikk",
                    "created_at": now,
                    "updated_at": now,
                    "last_health_check": now,
                    "connector_definition": {"endpoints": []},
                    "metadata": {}
                }
            ]
        
        # Remove old hardcoded data - now loaded from JSON above
        # sample_integrations is already set from JSON file or fallback
        
        for integration_data in sample_integrations:
            integration = Integration(**integration_data)
            self.integrations[integration.id] = integration
        
        return  # Skip old hardcoded data below
        
        old_sample_integrations_removed = [
            {
                "id": "shopify",
                "name": "Shopify",
                "version": "2.1.0",
                "category": "E-commerce",
                "description": "E-commerce platform for online stores and retail point-of-sale systems",
                "icon": "🛒",
                "base_url": "https://api.shopify.com",
                "status": "published",
                "health_status": "healthy",
                "install_count": 15400,
                "rating": 4.8,
                "rating_count": 892,
                "tags": ["ecommerce", "retail", "payments"],
                "created_by_user_id": "brikk",
                "created_at": "2024-01-15T00:00:00Z",
                "updated_at": "2024-11-18T00:00:00Z",
                "last_health_check": now,
                "connector_definition": {
                    "endpoints": [
                        {"id": "list_products", "name": "List Products", "method": "GET", "path": "/admin/api/2024-01/products.json"},
                        {"id": "create_order", "name": "Create Order", "method": "POST", "path": "/admin/api/2024-01/orders.json"},
                        {"id": "get_customer", "name": "Get Customer", "method": "GET", "path": "/admin/api/2024-01/customers/{id}.json"}
                    ]
                }
            },
            {
                "id": "salesforce",
                "name": "Salesforce",
                "version": "3.0.1",
                "category": "CRM",
                "description": "Customer relationship management (CRM) platform for sales and marketing",
                "icon": "☁️",
                "base_url": "https://api.salesforce.com",
                "status": "published",
                "health_status": "healthy",
                "install_count": 23100,
                "rating": 4.7,
                "rating_count": 1245,
                "tags": ["crm", "sales", "marketing"],
                "created_by_user_id": "brikk",
                "created_at": "2024-01-10T00:00:00Z",
                "updated_at": "2024-11-15T00:00:00Z",
                "last_health_check": now,
                "connector_definition": {
                    "endpoints": [
                        {"id": "query", "name": "SOQL Query", "method": "GET", "path": "/services/data/v58.0/query"},
                        {"id": "create_lead", "name": "Create Lead", "method": "POST", "path": "/services/data/v58.0/sobjects/Lead"},
                        {"id": "update_opportunity", "name": "Update Opportunity", "method": "PATCH", "path": "/services/data/v58.0/sobjects/Opportunity/{id}"}
                    ]
                }
            },
            {
                "id": "netsuite",
                "name": "NetSuite",
                "version": "1.5.2",
                "category": "ERP",
                "description": "Cloud-based ERP system for financial management and business operations",
                "icon": "🏢",
                "base_url": "https://api.netsuite.com",
                "status": "published",
                "health_status": "healthy",
                "install_count": 8900,
                "rating": 4.6,
                "rating_count": 456,
                "tags": ["erp", "finance", "accounting"],
                "created_by_user_id": "brikk",
                "created_at": "2024-02-01T00:00:00Z",
                "updated_at": "2024-11-10T00:00:00Z",
                "last_health_check": now,
                "connector_definition": {
                    "endpoints": [
                        {"id": "get_customer", "name": "Get Customer", "method": "GET", "path": "/services/rest/record/v1/customer/{id}"},
                        {"id": "create_invoice", "name": "Create Invoice", "method": "POST", "path": "/services/rest/record/v1/invoice"},
                        {"id": "list_transactions", "name": "List Transactions", "method": "GET", "path": "/services/rest/record/v1/transaction"}
                    ]
                }
            },
            {
                "id": "stripe",
                "name": "Stripe",
                "version": "4.2.0",
                "category": "Finance",
                "description": "Payment processing platform for online and mobile commerce",
                "icon": "💳",
                "base_url": "https://api.stripe.com",
                "status": "published",
                "health_status": "healthy",
                "install_count": 31300,
                "rating": 4.9,
                "rating_count": 2103,
                "tags": ["payments", "finance", "billing"],
                "created_by_user_id": "brikk",
                "created_at": "2024-01-05T00:00:00Z",
                "updated_at": "2024-11-18T00:00:00Z",
                "last_health_check": now,
                "connector_definition": {
                    "endpoints": [
                        {"id": "create_payment_intent", "name": "Create Payment Intent", "method": "POST", "path": "/v1/payment_intents"},
                        {"id": "list_customers", "name": "List Customers", "method": "GET", "path": "/v1/customers"},
                        {"id": "create_subscription", "name": "Create Subscription", "method": "POST", "path": "/v1/subscriptions"}
                    ]
                }
            },
            {
                "id": "shipbob",
                "name": "ShipBob",
                "version": "2.0.3",
                "category": "Logistics",
                "description": "Fulfillment and logistics platform for e-commerce businesses",
                "icon": "📦",
                "base_url": "https://api.shipbob.com",
                "status": "published",
                "health_status": "healthy",
                "install_count": 6800,
                "rating": 4.5,
                "rating_count": 234,
                "tags": ["logistics", "shipping", "fulfillment"],
                "created_by_user_id": "brikk",
                "created_at": "2024-03-01T00:00:00Z",
                "updated_at": "2024-11-12T00:00:00Z",
                "last_health_check": now,
                "connector_definition": {
                    "endpoints": [
                        {"id": "create_order", "name": "Create Order", "method": "POST", "path": "/1.0/order"},
                        {"id": "get_inventory", "name": "Get Inventory", "method": "GET", "path": "/1.0/inventory"},
                        {"id": "track_shipment", "name": "Track Shipment", "method": "GET", "path": "/1.0/shipment/{id}"}
                    ]
                }
            },
            {
                "id": "gmail",
                "name": "Gmail",
                "version": "1.8.0",
                "category": "Communication",
                "description": "Email service by Google with powerful search and organization features",
                "icon": "📧",
                "base_url": "https://gmail.googleapis.com",
                "status": "published",
                "health_status": "healthy",
                "install_count": 45600,
                "rating": 4.8,
                "rating_count": 3421,
                "tags": ["email", "communication", "google"],
                "created_by_user_id": "brikk",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-11-17T00:00:00Z",
                "last_health_check": now,
                "connector_definition": {
                    "endpoints": [
                        {"id": "send_email", "name": "Send Email", "method": "POST", "path": "/gmail/v1/users/me/messages/send"},
                        {"id": "list_messages", "name": "List Messages", "method": "GET", "path": "/gmail/v1/users/me/messages"},
                        {"id": "get_message", "name": "Get Message", "method": "GET", "path": "/gmail/v1/users/me/messages/{id}"}
                    ]
                }
            },
            {
                "id": "sap",
                "name": "SAP",
                "version": "5.1.0",
                "category": "ERP",
                "description": "Enterprise resource planning software for large organizations",
                "icon": "🏭",
                "base_url": "https://api.sap.com",
                "status": "published",
                "health_status": "healthy",
                "install_count": 12300,
                "rating": 4.4,
                "rating_count": 678,
                "tags": ["erp", "enterprise", "manufacturing"],
                "created_by_user_id": "brikk",
                "created_at": "2024-02-15T00:00:00Z",
                "updated_at": "2024-11-14T00:00:00Z",
                "last_health_check": now,
                "connector_definition": {
                    "endpoints": [
                        {"id": "get_material", "name": "Get Material", "method": "GET", "path": "/sap/opu/odata/sap/API_MATERIAL_STOCK_SRV/A_MaterialStock('{id}')"},
                        {"id": "create_purchase_order", "name": "Create Purchase Order", "method": "POST", "path": "/sap/opu/odata/sap/API_PURCHASEORDER_PROCESS_SRV/A_PurchaseOrder"},
                        {"id": "list_sales_orders", "name": "List Sales Orders", "method": "GET", "path": "/sap/opu/odata/sap/API_SALES_ORDER_SRV/A_SalesOrder"}
                    ]
                }
            },
            {
                "id": "oracle",
                "name": "Oracle",
                "version": "3.5.1",
                "category": "Database",
                "description": "Database and cloud solutions for enterprise applications",
                "icon": "🗄️",
                "base_url": "https://api.oracle.com",
                "status": "published",
                "health_status": "healthy",
                "install_count": 9900,
                "rating": 4.3,
                "rating_count": 543,
                "tags": ["database", "cloud", "enterprise"],
                "created_by_user_id": "brikk",
                "created_at": "2024-02-20T00:00:00Z",
                "updated_at": "2024-11-13T00:00:00Z",
                "last_health_check": now,
                "connector_definition": {
                    "endpoints": [
                        {"id": "query_database", "name": "Query Database", "method": "POST", "path": "/ords/hr/query"},
                        {"id": "get_table_data", "name": "Get Table Data", "method": "GET", "path": "/ords/hr/{table}"},
                        {"id": "execute_procedure", "name": "Execute Procedure", "method": "POST", "path": "/ords/hr/procedure/{name}"}
                    ]
                }
            }
        ]
        
        for integration_data in sample_integrations:
            integration = Integration(**integration_data)
            self.integrations[integration.id] = integration
    
    # ========================================================================
    # INTEGRATION CRUD
    # ========================================================================
    
    def list_integrations(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None,
        status: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> List[Integration]:
        """List integrations with optional filters"""
        results = list(self.integrations.values())
        
        if category:
            results = [i for i in results if i.category.lower() == category.lower()]
        
        if search:
            search_lower = search.lower()
            results = [
                i for i in results 
                if search_lower in i.name.lower() or search_lower in i.description.lower()
            ]
        
        if status:
            results = [i for i in results if i.status == status]
        
        if created_by:
            results = [i for i in results if i.created_by_user_id == created_by]
        
        # Sort by install count descending
        results.sort(key=lambda x: x.install_count, reverse=True)
        
        return results
    
    def get_integration(self, integration_id: str) -> Optional[Integration]:
        """Get integration by ID"""
        return self.integrations.get(integration_id)
    
    def create_integration(
        self,
        request: CreateIntegrationRequest,
        user_id: str
    ) -> Integration:
        """Create new integration"""
        # Generate ID from name
        integration_id = request.name.lower().replace(" ", "-").replace("_", "-")
        
        # Check if already exists
        if integration_id in self.integrations:
            raise HTTPException(status_code=400, detail="Integration with this name already exists")
        
        now = datetime.utcnow().isoformat()
        
        integration = Integration(
            id=integration_id,
            name=request.name,
            version="1.0.0",
            category=request.category,
            description=request.description,
            icon=request.icon,
            base_url=request.base_url,
            status="draft",
            health_status="healthy",
            install_count=0,
            rating=0.0,
            rating_count=0,
            tags=[],
            created_by_user_id=user_id,
            created_at=now,
            updated_at=now,
            connector_definition=request.connector_definition
        )
        
        self.integrations[integration_id] = integration
        return integration
    
    def update_integration(
        self,
        integration_id: str,
        request: UpdateIntegrationRequest,
        user_id: str
    ) -> Integration:
        """Update existing integration"""
        integration = self.integrations.get(integration_id)
        if not integration:
            raise HTTPException(status_code=404, detail="Integration not found")
        
        # Check ownership
        if integration.created_by_user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to update this integration")
        
        # Update fields
        if request.name is not None:
            integration.name = request.name
        if request.category is not None:
            integration.category = request.category
        if request.description is not None:
            integration.description = request.description
        if request.icon is not None:
            integration.icon = request.icon
        if request.base_url is not None:
            integration.base_url = request.base_url
        if request.status is not None:
            integration.status = request.status
        if request.connector_definition is not None:
            integration.connector_definition = request.connector_definition
        
        integration.updated_at = datetime.utcnow().isoformat()
        
        return integration
    
    def delete_integration(self, integration_id: str, user_id: str):
        """Delete integration"""
        integration = self.integrations.get(integration_id)
        if not integration:
            raise HTTPException(status_code=404, detail="Integration not found")
        
        # Check ownership
        if integration.created_by_user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this integration")
        
        del self.integrations[integration_id]
    
    # ========================================================================
    # INSTALLATION MANAGEMENT
    # ========================================================================
    
    def install_integration(self, integration_id: str, user_id: str):
        """Install integration for user"""
        integration = self.integrations.get(integration_id)
        if not integration:
            raise HTTPException(status_code=404, detail="Integration not found")
        
        # Check if already installed
        user_installations = self.installations.get(user_id, [])
        if any(i.integration_id == integration_id for i in user_installations):
            raise HTTPException(status_code=400, detail="Integration already installed")
        
        # Create installation record
        installation = IntegrationInstallation(
            integration_id=integration_id,
            user_id=user_id,
            installed_at=datetime.utcnow().isoformat(),
            version=integration.version
        )
        
        if user_id not in self.installations:
            self.installations[user_id] = []
        self.installations[user_id].append(installation)
        
        # Increment install count
        integration.install_count += 1
        
        return installation
    
    def uninstall_integration(self, integration_id: str, user_id: str):
        """Uninstall integration for user"""
        integration = self.integrations.get(integration_id)
        if not integration:
            raise HTTPException(status_code=404, detail="Integration not found")
        
        user_installations = self.installations.get(user_id, [])
        installation = next((i for i in user_installations if i.integration_id == integration_id), None)
        
        if not installation:
            raise HTTPException(status_code=404, detail="Integration not installed")
        
        # Remove installation
        user_installations.remove(installation)
        
        # Decrement install count
        integration.install_count = max(0, integration.install_count - 1)
    
    def get_user_installations(self, user_id: str) -> List[IntegrationInstallation]:
        """Get all installations for user"""
        return self.installations.get(user_id, [])
    
    def is_installed(self, integration_id: str, user_id: str) -> bool:
        """Check if integration is installed for user"""
        user_installations = self.installations.get(user_id, [])
        return any(i.integration_id == integration_id for i in user_installations)
    
    # ========================================================================
    # CATEGORIES
    # ========================================================================
    
    def get_categories(self) -> List[Dict[str, Any]]:
        """Get all integration categories with counts"""
        categories = {}
        
        for integration in self.integrations.values():
            category = integration.category
            if category not in categories:
                categories[category] = {"name": category, "count": 0}
            categories[category]["count"] += 1
        
        return list(categories.values())


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

integration_registry = IntegrationRegistry()
