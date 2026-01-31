# MSNA 2025 Analysis - Azure Deployment

Deployment guide for interactive Marimo notebooks on Azure Container Instances.

## Architecture

- **Service**: Azure Container Instances (ACI)
- **Registry**: Azure Container Registry (ACR)
- **Application**: Marimo notebooks (port 2718)
- **Data**: Parquet files embedded in Docker image
- **Access**: Public (no authentication)

## Prerequisites

1. Install Azure CLI:
   ```bash
   brew install azure-cli
   az --version
   ```

2. Authenticate:
   ```bash
   az login
   ```

3. Current configuration in `deploy-azure.sh`:
   - `RESOURCE_GROUP`: HQ-dev (existing)
   - `ACR_NAME`: acrimpact (existing)
   - `DNS_NAME_LABEL`: impact-msna-analysis-2025
   - `LOCATION`: switzerlandnorth

## Deployment

### Local Testing

```bash
# Using docker-compose
docker-compose up --build

# Direct Docker
docker build -t msna-analysis:local .
docker run -p 2718:2718 msna-analysis:local
```

Access at: http://localhost:2718

### Azure Deployment

**Full deployment (with build):**
```bash
chmod +x deploy-azure.sh
./deploy-azure.sh
```

**Quick deployment (skip build if image exists):**
```bash
SKIP_BUILD=true ./deploy-azure.sh
```

Deployment includes:
1. Resource group verification (HQ-dev)
2. Container registry verification (acrimpact)
3. Docker image build and push (optional)
4. Container instance deployment
5. Public URL generation

Deployment time: 
- Full build: 5-10 minutes
- Skip build: 1-2 minutes

## Management

**View logs:**
```bash
az container logs --resource-group HQ-dev --name msna-analysis --follow
```

**Check status:**
```bash
az container show --resource-group HQ-dev --name msna-analysis --query instanceView.state
```

**Restart container:**
```bash
az container restart --resource-group HQ-dev --name msna-analysis
```

**Update deployment:**
```bash
# Rebuild and redeploy
./deploy-azure.sh

# Or manually rebuild image
az acr build --registry acrimpact --image msna-analysis:latest --file Dockerfile .

# Then restart to pull new image
az container restart --resource-group HQ-dev --name msna-analysis
```

**Cost optimization:**
```bash
# Stop when not in use
az container stop --resource-group HQ-dev --name msna-analysis

# Start when needed
az container start --resource-group HQ-dev --name msna-analysis
```

## Resource Cleanup

**Delete container only:**
```bash
az container delete --resource-group HQ-dev --name msna-analysis --yes
```

**Delete resource group:**
```bash
# ⚠️ Warning: HQ-dev contains other resources
# Only delete if you're sure
az group delete --name HQ-dev --yes --no-wait
```

## Cost Estimate

- **ACI** (1 vCPU, 2 GB RAM, Switzerland North): ~€32/month (continuous operation)
- **ACR** (Basic SKU): Shared resource (existing acrimpact registry)

Stop container when unused to reduce costs. Per-second billing allows cost-effective usage.

## Troubleshooting

**Container not starting:**
```bash
az container logs --resource-group HQ-dev --name msna-analysis
az container show --resource-group HQ-dev --name msna-analysis --query instanceView.events
```

**DNS name conflict:**
Update `DNS_NAME_LABEL` in `deploy-azure.sh` to a unique value.

**Port not responding:**
- Verify container state is "Running"
- Allow 30-60 seconds for initial startup
- Check logs for errors
- Access URL: http://impact-msna-analysis-2025.switzerlandnorth.azurecontainer.io:2718

**Image size:**
Expected size: ~400-500 MB (Python runtime + dependencies + data)

**Build failures:**
- Azure ACR doesn't support BuildKit features (already removed from Dockerfile)
- Heredoc syntax converted to separate files for compatibility

## Security

Current deployment is **public** with no authentication.

For authentication, consider:
- Azure AD integration (App Service)
- Reverse proxy with basic auth
- Azure Application Gateway with WAF

## Resources

- [Azure Container Instances](https://docs.microsoft.com/azure/container-instances/)
- [Marimo Documentation](https://docs.marimo.io/)
- [Azure CLI Reference](https://docs.microsoft.com/cli/azure/)
