#!/bin/bash
# =============================================================================
# Deploy MSNA 2025 Analysis to Azure Container Instances
# =============================================================================

set -e  # Exit on error

# Configuration variables
RESOURCE_GROUP="HQ-dev"
LOCATION="switzerlandnorth"
CONTAINER_NAME="msna-analysis"
ACR_NAME="acrimpact"
IMAGE_NAME="msna-analysis"
IMAGE_TAG="latest"
DNS_NAME_LABEL="impact-msna-analysis-2025"  # Must be globally unique in Azure region
SKIP_BUILD="${SKIP_BUILD:-false}"  # Set to "true" to skip rebuild

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== MSNA 2025 Analysis - Azure Deployment ===${NC}\n"

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo -e "${RED}Error: Azure CLI is not installed${NC}"
    echo "Install from: https://docs.microsoft.com/cli/azure/install-azure-cli"
    exit 1
fi

# Check if logged in to Azure
echo -e "${BLUE}Checking Azure login...${NC}"
if ! az account show &> /dev/null; then
    echo -e "${RED}Error: Not logged in to Azure${NC}"
    echo "Run: az login"
    exit 1
fi

SUBSCRIPTION_ID=$(az account show --query id -o tsv)
SUBSCRIPTION_NAME=$(az account show --query name -o tsv)
echo -e "${GREEN}✓ Logged in to subscription: ${SUBSCRIPTION_NAME}${NC}\n"

# Step 1: Create Resource Group
echo -e "${BLUE}Step 1: Creating Resource Group...${NC}"
if az group show --name "$RESOURCE_GROUP" &> /dev/null; then
    echo -e "${GREEN}✓ Resource Group already exists${NC}"
else
    az group create --name "$RESOURCE_GROUP" --location "$LOCATION"
    echo -e "${GREEN}✓ Resource Group created${NC}"
fi
echo ""

# Step 2: Create Azure Container Registry
echo -e "${BLUE}Step 2: Creating Azure Container Registry...${NC}"
if az acr show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
    echo -e "${GREEN}✓ ACR already exists${NC}"
else
    az acr create \
        --resource-group "$RESOURCE_GROUP" \
        --name "$ACR_NAME" \
        --sku Basic \
        --admin-enabled true
    echo -e "${GREEN}✓ ACR created${NC}"
fi
echo ""

# Step 3: Build and Push Docker Image
echo -e "${BLUE}Step 3: Building and pushing Docker image...${NC}"
if [ "$SKIP_BUILD" = "true" ]; then
    echo -e "${GREEN}✓ Skipping build (SKIP_BUILD=true)${NC}"
else
    az acr build \
        --registry "$ACR_NAME" \
        --image "${IMAGE_NAME}:${IMAGE_TAG}" \
        --file Dockerfile \
        .
    echo -e "${GREEN}✓ Image built and pushed to ACR${NC}"
fi
echo ""

# Step 4: Get ACR credentials
echo -e "${BLUE}Step 4: Getting ACR credentials...${NC}"
ACR_LOGIN_SERVER=$(az acr show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" --query loginServer -o tsv)
ACR_USERNAME=$(az acr credential show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" --query username -o tsv)
ACR_PASSWORD=$(az acr credential show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" --query passwords[0].value -o tsv)
echo -e "${GREEN}✓ Credentials retrieved${NC}\n"

# Step 5: Deploy to Azure Container Instances
echo -e "${BLUE}Step 5: Deploying to Azure Container Instances...${NC}"
az container create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$CONTAINER_NAME" \
    --image "${ACR_LOGIN_SERVER}/${IMAGE_NAME}:${IMAGE_TAG}" \
    --registry-login-server "$ACR_LOGIN_SERVER" \
    --registry-username "$ACR_USERNAME" \
    --registry-password "$ACR_PASSWORD" \
    --dns-name-label "$DNS_NAME_LABEL" \
    --ports 2718 \
    --cpu 1 \
    --memory 2 \
    --os-type Linux \
    --restart-policy Always

echo -e "${GREEN}✓ Container deployed${NC}\n"

# Step 6: Get public URL
FQDN=$(az container show \
    --resource-group "$RESOURCE_GROUP" \
    --name "$CONTAINER_NAME" \
    --query ipAddress.fqdn -o tsv)

echo -e "${GREEN}=== Deployment Complete! ===${NC}\n"
echo -e "Your MSNA Analysis notebooks are available at:"
echo -e "${BLUE}http://${FQDN}:2718${NC}\n"
echo -e "To view logs:"
echo -e "  az container logs --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME\n"
echo -e "To stop the container:"
echo -e "  az container stop --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME\n"
echo -e "To delete resources:"
echo -e "  az group delete --name $RESOURCE_GROUP --yes --no-wait\n"
