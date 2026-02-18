# Deployment Guide

## Prerequisites

- Docker Desktop 4.38+ (with Kubernetes enabled)
- kubectl 1.29+
- kind 0.20+
- 8GB+ RAM available
- PowerShell 5.0+ (for deploy script)

## Local Development (Kind)

### 1. Create Kind Cluster

```bash
kind create cluster --name tax-ai-demo --config infra/kubernetes/docker-desktop/kind-config.yaml
```

**Verify:**
```bash
kubectl cluster-info
kubectl get nodes
```

### 2. Deploy All Manifests

```powershell
# Using deployment script
./scripts/deploy.ps1
```

**Or manually:**
```bash
# Create namespace
kubectl apply -f infra/kubernetes/docker-desktop/ns.yaml

# Deploy services in order
kubectl apply -f infra/kubernetes/docker-desktop/redis.yaml
kubectl apply -f infra/kubernetes/docker-desktop/phi3-vllm.yaml
kubectl apply -f infra/kubernetes/docker-desktop/tax-api.yaml
```

### 3. Verify Deployments

```bash
# Check namespace
kubectl get ns | grep tax-ai

# Check pods
kubectl get pods -n tax-ai -w

# Wait for ready
kubectl wait --for=condition=Ready pod -l app=tax-api -n tax-ai --timeout=300s
```

### 4. Port Forward

```bash
# API
kubectl port-forward svc/tax-api 8080:80 -n tax-ai

# In another terminal - Phi-3 vLLM metrics
kubectl port-forward svc/phi3-vllm 8000:8000 -n tax-ai
```

### 5. Test

```bash
# Health check
curl http://localhost:8080/

# Fast path (Phi-3)
curl -X POST http://localhost:8080/ai-tax \
  -H "Content-Type: application/json" \
  -d '{"amount": 100000, "jurisdictions": ["US"]}'

# Legacy path
curl -X POST http://localhost:8080/ai-tax \
  -H "Content-Type: application/json" \
  -d '{"amount": 5000000, "jurisdictions": ["US", "CA", "UK"]}'
```

## Cleanup

### Delete Kind Cluster

```bash
kind delete cluster --name tax-ai-demo
```

### Delete Namespace (Keep Cluster)

```bash
kubectl delete namespace tax-ai
```

## Building and Pushing Docker Image

### Build Locally

```bash
docker build -t tax-calc-api:latest -f infra/docker/Dockerfile .
```

### Push to Registry

```bash
# Set your registry
REGISTRY="your-registry.azurecr.io"
IMAGE_NAME="tax-calc-api"
TAG="v0.1.0"

# Build and push
docker build -t $REGISTRY/$IMAGE_NAME:$TAG -f infra/docker/Dockerfile .
docker push $REGISTRY/$IMAGE_NAME:$TAG

# Update manifest reference
# Edit infra/kubernetes/docker-desktop/tax-api.yaml
# Change: image: tax-calc-api:latest
# To: image: $REGISTRY/$IMAGE_NAME:$TAG
```

## Production Deployment

### Azure Kubernetes Service (AKS)

1. **Create AKS Cluster:**
```bash
az aks create \
  --resource-group myResourceGroup \
  --name tax-ai-prod \
  --node-count 3 \
  --vm-set-type VirtualMachineScaleSets \
  --load-balancer-sku standard
```

2. **Get Credentials:**
```bash
az aks get-credentials \
  --resource-group myResourceGroup \
  --name tax-ai-prod
```

3. **Deploy Stack:**
```bash
kubectl apply -f infra/kubernetes/docker-desktop/
```

4. **Create Ingress:**
```bash
kubectl apply -f infra/kubernetes/ingress.yaml
```

### GKE (Google Cloud)

```bash
gcloud container clusters create tax-ai-prod \
  --zone us-central1-a \
  --num-nodes 3 \
  --machine-type n1-standard-4

gcloud container clusters get-credentials tax-ai-prod \
  --zone us-central1-a
```

## Monitoring & Logging

### View Logs

```bash
# API logs
kubectl logs -f deployment/tax-api -n tax-ai

# Phi-3 vLLM logs
kubectl logs -f deployment/phi3-vllm -n tax-ai

# Redis logs
kubectl logs -f deployment/redis -n tax-ai

# Follow pod creation (debug)
kubectl logs -f pod/tax-api-xxx -n tax-ai --all-containers=true
```

### Metrics

```bash
# Pod resource usage
kubectl top pods -n tax-ai

# Node resource usage
kubectl top nodes

# HPA status
kubectl get hpa -n tax-ai -w
```

### Access Redis CLI

```bash
kubectl exec -it $(kubectl get pods -n tax-ai -l app=redis -o jsonpath='{.items[0].metadata.name}') -n tax-ai -- redis-cli

# Inside Redis CLI
> KEYS "*"
> GET phi3_calls
> GET legacy_calls
```

## Troubleshooting

### Pods Not Starting

```bash
# Check events
kubectl describe pod <pod-name> -n tax-ai

# Check resource constraints
kubectl describe node

# Check image pull
kubectl get events -n tax-ai --sort-by='.lastTimestamp'
```

### Network Issues

```bash
# Test DNS
kubectl run -it --rm debug --image=nicolaka/netshoot -n tax-ai -- bash

# Inside container
nslookup tax-api.tax-ai.svc.cluster.local
nslookup phi3-vllm.tax-ai.svc.cluster.local

# Test connectivity
curl http://tax-api.tax-ai.svc.cluster.local/
```

### Memory Issues (Phi-3)

```bash
# Increase memory limit
kubectl set resources deployment phi3-vllm -n tax-ai \
  --limits=memory=6Gi,cpu=2 \
  --requests=memory=4Gi,cpu=1

# Restart pod
kubectl rollout restart deployment/phi3-vllm -n tax-ai
```

### Performance Issues

```bash
# Check HPA scaling
kubectl get hpa -n tax-ai -w

# Check metrics server (required for HPA)
kubectl get deployment metrics-server -n kube-system

# If missing, install:
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

## Scaling

### Manual Scaling

```bash
# Scale tax-api
kubectl scale deployment tax-api --replicas=5 -n tax-ai

# Scale phi3-vllm
kubectl scale deployment phi3-vllm --replicas=3 -n tax-ai
```

### Autoscaling

```bash
# Check HPA rules
kubectl describe hpa -n tax-ai

# Edit HPA
kubectl edit hpa -n tax-ai
```

## Rolling Updates

```bash
# Update image
kubectl set image deployment/tax-api \
  tax-api=your-registry/tax-calc-api:v0.2.0 \
  -n tax-ai --record

# Monitor rollout
kubectl rollout status deployment/tax-api -n tax-ai

# Rollback if needed
kubectl rollout undo deployment/tax-api -n tax-ai
```
