#!/bin/bash

# Brikk UCS Backend - Deployment Verification Script
# Usage: ./test_deployment.sh <RAILWAY_URL>

if [ -z "$1" ]; then
    echo "❌ Error: Railway URL required"
    echo "Usage: ./test_deployment.sh https://your-railway-url.up.railway.app"
    exit 1
fi

RAILWAY_URL=$1
echo "🧪 Testing Brikk UCS Backend at: $RAILWAY_URL"
echo ""

# Test 1: Health Check
echo "Test 1: Health Check"
echo "GET $RAILWAY_URL/health"
HEALTH=$(curl -s "$RAILWAY_URL/health")
if echo "$HEALTH" | grep -q "healthy"; then
    echo "✅ PASS - Server is healthy"
else
    echo "❌ FAIL - Server health check failed"
    echo "Response: $HEALTH"
fi
echo ""

# Test 2: List Integrations
echo "Test 2: List Integrations"
echo "GET $RAILWAY_URL/api/v1/integrations"
INTEGRATIONS=$(curl -s "$RAILWAY_URL/api/v1/integrations")
COUNT=$(echo "$INTEGRATIONS" | grep -o '"total":[0-9]*' | grep -o '[0-9]*')
if [ "$COUNT" = "56" ]; then
    echo "✅ PASS - Found 56 integrations"
else
    echo "❌ FAIL - Expected 56 integrations, found: $COUNT"
fi
echo ""

# Test 3: Get Specific Integration
echo "Test 3: Get Shopify Integration"
echo "GET $RAILWAY_URL/api/v1/integrations/shopify"
SHOPIFY=$(curl -s "$RAILWAY_URL/api/v1/integrations/shopify")
if echo "$SHOPIFY" | grep -q "Shopify"; then
    echo "✅ PASS - Shopify integration found"
else
    echo "❌ FAIL - Shopify integration not found"
fi
echo ""

# Test 4: Install Integration
echo "Test 4: Install Integration"
echo "POST $RAILWAY_URL/api/v1/integrations/gmail/install"
INSTALL=$(curl -s -X POST "$RAILWAY_URL/api/v1/integrations/gmail/install" \
    -H "Content-Type: application/json" \
    -d '{"user_id": "test-user-123"}')
if echo "$INSTALL" | grep -q "success"; then
    echo "✅ PASS - Integration installed successfully"
else
    echo "❌ FAIL - Integration install failed"
    echo "Response: $INSTALL"
fi
echo ""

# Test 5: Connector Generation (Text)
echo "Test 5: Connector Generation from Text"
echo "POST $RAILWAY_URL/api/v1/ucs/generate/text"
GENERATE=$(curl -s -X POST "$RAILWAY_URL/api/v1/ucs/generate/text" \
    -H "Content-Type: application/json" \
    -d '{
        "text": "Stripe API has endpoints for creating customers and charges. Base URL is https://api.stripe.com/v1",
        "integration_name": "Stripe Test",
        "category": "Finance"
    }')
if echo "$GENERATE" | grep -q "connector"; then
    echo "✅ PASS - Connector generated successfully"
else
    echo "⚠️  WARNING - Connector generation may require OpenAI API key"
    echo "Response: $GENERATE"
fi
echo ""

# Summary
echo "=========================================="
echo "🎉 Deployment Verification Complete!"
echo "=========================================="
echo ""
echo "Next Steps:"
echo "1. Update dashboard VITE_UCS_API_URL to: $RAILWAY_URL"
echo "2. Redeploy dashboard on Netlify/Vercel"
echo "3. Test Integration Marketplace in dashboard"
echo "4. Test Integration Builder with sample API docs"
echo ""
echo "Documentation:"
echo "- API Docs: $RAILWAY_URL/docs"
echo "- Health: $RAILWAY_URL/health"
echo "- GitHub: https://github.com/eritger1110/brikk-ucs-backend"
