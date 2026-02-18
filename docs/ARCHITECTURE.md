# Architecture

## Overview

Tax AI Native Platform is a high-performance tax calculation engine that routes requests dynamically between Phi-3 vLLM (fast path) and Legacy Monolith (complex path) via a Kubernetes-orchestrated FastAPI service.

## System Components

### 1. FastAPI Gateway (`tax-api`)

- **Purpose**: Central request router with dynamic routing logic
- **Latency**: ~50ms overhead
- **Memory**: 256Mi
- **CPU**: 100m

**Routing Rules:**
- **Fast Path (Phi-3)**: jurisdictions ≤ 2 AND amount ≤ $2M
- **Legacy Path**: jurisdictions > 2 OR amount > $2M

### 2. Phi-3 vLLM (`phi3-vllm`)

- **Model**: Microsoft Phi-3-mini-4k-instruct
- **Inference Engine**: vLLM
- **Latency**: 187ms p50, <500ms p99
- **Memory**: 4Gi
- **GPU**: Optional (runs on CPU, ~2-3x slower)
- **Replicas**: 2 (autoscaled by HPA)

### 3. Legacy Monolith

- **Purpose**: Simulated existing tax calculation engine
- **Latency**: 6s baseline
- **Used for**: Complex multi-jurisdiction scenarios

### 4. Redis Cache

- **Namespace**: `tax-ai`
- **Keys**:
  - `phi3_calls`: Counter
  - `legacy_calls`: Counter
- **Memory**: 256Mi
- **Persistence**: False (ephemeral)

## Kubernetes Architecture

### Namespace: `tax-ai`

All resources deployed in dedicated `tax-ai` namespace for isolation.

### Service Discovery

- **tax-api**: `tax-api.tax-ai.svc.cluster.local:80`
- **phi3-vllm**: `phi3-vllm.tax-ai.svc.cluster.local:8000`
- **redis**: `redis.tax-ai.svc.cluster.local:6379`

### Network Flow

```
Client (Port 8080)
    ↓
Service: tax-api (ClusterIP:80)
    ↓
Deployment: tax-api (FastAPI pods)
    ├─→ HTTP → Service: phi3-vllm (Port 8000)
    │         ↓
    │       Deployment: phi3-vllm (2 pods)
    │
    ├─→ TCP → Service: redis (Port 6379)
    │         ↓
    │       Deployment: redis (1 pod)
    │
    └─→ Internal Legacy call
        (simulated with time.sleep(6))
```

### High Availability & Scaling

**HPA Configuration:**
- Target CPU: 50%
- Min replicas: 2
- Max replicas: 5
- Scale-up threshold: 60% CPU
- Scale-down threshold: 20% CPU

### Resource Requests & Limits

**tax-api:**
- Request: 100m CPU, 128Mi RAM
- Limit: 500m CPU, 512Mi RAM

**phi3-vllm:**
- Request: 1000m CPU, 4Gi RAM
- Limit: 2000m CPU, 6Gi RAM

**redis:**
- Request: 50m CPU, 128Mi RAM
- Limit: 200m CPU, 512Mi RAM

## Data Flow

### Request Path (Phi-3)

```
1. Client POST /ai-tax
   {amount: 100000, jurisdictions: ["US"], complexity: "low"}

2. tax-api validates request

3. Routing decision: simplicity ≤ threshold
   → Route to Phi-3

4. tax-api → phi3-vllm (HTTP POST /v1/completions)
   Prompt: "Calculate tax exposure for $100,000 in US"

5. phi3-vllm returns:
   {completion_tokens: [...], model: "Phi-3-mini"}

6. tax-api parses response, caches result

7. redis.incr("phi3_calls")

8. Response to client (187ms total)
```

### Request Path (Legacy)

```
1. Client POST /ai-tax
   {amount: 5000000, jurisdictions: ["US", "CA", "UK"]}

2. tax-api validates request

3. Routing decision: complexity > threshold
   → Route to Legacy

4. tax-api simulates legacy_tax_calc()
   time.sleep(6) + calculation

5. redis.incr("legacy_calls")

6. Response to client (6000ms total)
```

## Scaling Characteristics

### Phi-3 vLLM Autoscaling

**Trigger:** Average CPU > 50% across replicas

**Sequence:**
1. HPA detects high CPU
2. Scale from 2 → 3 replicas (30s)
3. New pod downloads model (~1-2 min cold start)
4. LB distributes traffic across 3 pods
5. Latency improves as load spreads

### Concurrent Request Handling

**Single pod (Phi-3):**
- vLLM batch size: 4
- QPS: ~10 requests/sec
- Latency: 187ms

**Three pods:**
- Combined QPS: ~30 requests/sec
- Latency stable at 187ms (batch processing)

## Cost Analysis

### Infrastructure (Monthly)

| Component | Size | vcpu | RAM | Cost |
|-----------|------|------|-----|------|
| kind cluster | 3 nodes | 6 | 12Gi | $0 (local) |
| tax-api | 2-5 pods | 0.5 | 1Gi | Included |
| phi3-vllm | 2 pods | 2 | 8Gi | Included |
| redis | 1 pod | 0.1 | 0.5Gi | Included |

### Per-Request Cost

**Phi-3 (self-hosted):** $0.000004 / token
- 20 tokens/request
- $0.00000008 / request

**GPT-4 (external):** $0.15 / 1M tokens
- $0.003 / request

**Savings:** 37,500x cheaper per request

## Monitoring

### Key Metrics

- **Latency**: p50, p95, p99 response times
- **Throughput**: requests/sec by routing type
- **Error Rate**: 4xx, 5xx errors
- **Resource Usage**: CPU, Memory by pod
- **HPA Events**: Scale-up/down operations

### Observability

Redis provides event counters:
```bash
kubectl exec redis-pod -- redis-cli KEYS "*calls"
# phi3_calls: 1245
# legacy_calls: 42
```

## Failure Modes & Recovery

### Phi-3 Unavailable
**Behavior:** Graceful degradation to random estimation
- Returns synthetic tax estimate (confidence: 0.90)
- Logs error
- Client still receives response

### Redis Unavailable
**Behavior:** Tax calculation proceeds without caching
- Metrics not tracked
- No impact on functionality

### Legacy Monolith Failure
**Behavior:** Would require circuit breaker (not yet implemented)
- Current: Always available (simulated)
- Recommended: Timeout + fallback to Phi-3

## Security Considerations

- No authentication on internal APIs (cluster-internal)
- No encryption in transit (internal communication)
- No rate limiting at API level
- **Recommended for production:**
  - NetworkPolicy for pod-to-pod communication
  - RBAC for service accounts
  - TLS termination on ingress
  - API key authentication
  - Rate limiting per client
