# API Reference

## Base URL

- **Development**: `http://localhost:8080`
- **Production**: `https://api.tax-ai.example.com`

## Endpoints

### GET /

Health check endpoint.

**Response:**
```json
{
  "message": "Tax AI Native Platform"
}
```

---

### POST /ai-tax

Main AI-native tax calculation endpoint with dynamic routing.

**Request:**
```json
{
  "amount": 100000,
  "jurisdictions": ["US", "CA"],
  "complexity": "low"
}
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `amount` | float | Yes | Tax exposure amount in USD |
| `jurisdictions` | array[string] | Yes | List of jurisdiction codes (e.g., ["US", "CA", "UK"]) |
| `complexity` | string | No | Hint for routing: "low" or "high" (default: "low") |

**Response (Phi-3 Fast Path):**

Status: `200 OK`

```json
{
  "tax": 21000,
  "confidence": 0.94,
  "latency_ms": 187.5,
  "engine": "Phi-3",
  "routing_reason": "simple_fast_path"
}
```

**Response (Legacy Path):**

Status: `200 OK`

```json
{
  "tax": 21000,
  "latency_ms": 6045.2,
  "engine": "Legacy Monolith",
  "routing_reason": "high_complexity_or_large_amount"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `tax` | float | Calculated tax exposure |
| `confidence` | float | AI confidence level (0.0-1.0), only in Phi-3 responses |
| `latency_ms` | float | Request processing time in milliseconds |
| `engine` | string | Which engine processed request ("Phi-3" or "Legacy Monolith") |
| `routing_reason` | string | Explanation of routing decision |

**Error Responses:**

```json
{
  "detail": "Error message"
}
```

| Status | Description |
|--------|-------------|
| `400` | Invalid request parameters |
| `422` | Validation error |
| `500` | Server error |
| `503` | Service unavailable |

---

### POST /legacy-tax-calc

Direct call to legacy monolith (for benchmarking).

**Request:**
```json
{
  "amount": 100000,
  "jurisdictions": ["US"]
}
```

**Response:**
```json
{
  "tax": 21000,
  "latency": "6000ms",
  "engine": "Monolith"
}
```

---

## Examples

### Example 1: Simple Single Jurisdiction Request (Fast Path)

```bash
curl -X POST http://localhost:8080/ai-tax \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 50000,
    "jurisdictions": ["US"],
    "complexity": "low"
  }'
```

**Response:**
```json
{
  "tax": 10500,
  "confidence": 0.91,
  "latency_ms": 165.3,
  "engine": "Phi-3",
  "routing_reason": "simple_fast_path"
}
```

### Example 2: Complex Multi-Jurisdiction Request (Legacy Path)

```bash
curl -X POST http://localhost:8080/ai-tax \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 3000000,
    "jurisdictions": ["US", "CA", "UK", "DE"],
    "complexity": "high"
  }'
```

**Response:**
```json
{
  "tax": 690000,
  "latency_ms": 6012.1,
  "engine": "Legacy Monolith",
  "routing_reason": "high_complexity_or_large_amount"
}
```

### Example 3: Large Amount (Automatic Legacy Path)

```bash
curl -X POST http://localhost:8080/ai-tax \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 5000000,
    "jurisdictions": ["US"]
  }'
```

**Response:**
```json
{
  "tax": 1050000,
  "latency_ms": 6008.5,
  "engine": "Legacy Monolith",
  "routing_reason": "high_complexity_or_large_amount"
}
```

---

## Routing Logic

The `/ai-tax` endpoint automatically routes requests based on complexity:

### Phi-3 Path (Fast ~187ms)
**Conditions:**
- `jurisdictions.length ≤ 2` AND
- `amount ≤ $2,000,000`

### Legacy Path (Slow ~6s)
**Conditions:**
- `jurisdictions.length > 2` OR
- `amount > $2,000,000`

### Logic Flow

```
POST /ai-tax
    ↓
Validate input
    ↓
Calculate: jurisdictions_count = len(request.jurisdictions)
Calculate: is_complex = (jurisdictions_count > 2 OR amount > 2M)
    ↓
    ├─→ is_complex = False → Phi-3 Path
    │   - Call phi3-vllm
    │   - Latency: ~187ms
    │   - Includes confidence score
    │
    └─→ is_complex = True → Legacy Path
        - Simulate monolith
        - Latency: ~6000ms
        - Includes engine hint
```

---

## Performance Characteristics

### Latency Distribution

**Phi-3 Path:**
- p50: 160ms
- p95: 220ms
- p99: 350ms

**Legacy Path:**
- p50: 6000ms
- p95: 6050ms
- p99: 6100ms

### Throughput

**Per Instance:**
- Phi-3: ~10 req/sec (batch size 4)
- Legacy: ~1 req/sec (6s processing)

**Clustered (2x Phi-3 replicas, HPA up to 5x):**
- Phi-3: Up to 50 req/sec
- Legacy: Up to 5 req/sec

### Resource Usage

**Phi-3 Path:**
- CPU: 200-400m
- Memory: 300-500Mi
- Network: ~5KB request/response

**Legacy Path:**
- CPU: 50m
- Memory: 50Mi
- Network: ~2KB request/response

---

## Error Handling

### Graceful Degradation

If Phi-3 vLLM service is unavailable, the `/ai-tax` endpoint:
1. Catches the connection error
2. Returns synthetic tax estimate
3. Sets confidence to 0.85-0.95 (degraded)
4. Logs the error
5. Still returns HTTP 200 (not a client error)

**Degraded Response:**
```json
{
  "tax": 18500,
  "confidence": 0.89,
  "latency_ms": 45.2,
  "engine": "Phi-3",
  "routing_reason": "simple_fast_path",
  "note": "Degraded: service unavailable"
}
```

### Validation Errors

```bash
# Missing required field
curl -X POST http://localhost:8080/ai-tax \
  -H "Content-Type: application/json" \
  -d '{"amount": 100000}'
```

**Response:**
```json
{
  "detail": [
    {
      "type": "value_error.missing",
      "loc": ["body", "jurisdictions"],
      "msg": "field required"
    }
  ]
}
```

---

## Rate Limiting & Quotas

**Current:** No rate limiting implemented

**Recommended for Production:**
- 100 req/sec per client IP
- 10,000 req/day per API key
- Burst allowance: 500 req/10sec

---

## Versioning

**Current Version:** v0 (unversioned)

**Planned:**
- v1: Add authentication & rate limiting
- v2: Add batch endpoint
- v3: Add custom model selection

---

## SDK / Client Libraries

### Python Example

```python
import httpx
import asyncio

async def calculate_tax(amount: float, jurisdictions: list[str]):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8080/ai-tax",
            json={
                "amount": amount,
                "jurisdictions": jurisdictions,
                "complexity": "low"
            }
        )
        return response.json()

# Usage
result = asyncio.run(calculate_tax(100000, ["US", "CA"]))
print(f"Tax: ${result['tax']}, Engine: {result['engine']}")
```

### JavaScript/Node.js Example

```javascript
async function calculateTax(amount, jurisdictions) {
  const response = await fetch('http://localhost:8080/ai-tax', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      amount,
      jurisdictions,
      complexity: 'low'
    })
  });
  return response.json();
}

// Usage
const result = await calculateTax(100000, ['US', 'CA']);
console.log(`Tax: $${result.tax}, Engine: ${result.engine}`);
```

---

## Support

For API issues or questions:
1. Check [ARCHITECTURE.md](ARCHITECTURE.md) for system design
2. Check [DEPLOYMENT.md](DEPLOYMENT.md) for troubleshooting
3. Open an issue on [GitHub](https://github.com/yourusername/tax-ai-native-k8s)
