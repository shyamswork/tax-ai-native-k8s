<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# please write this readme file content to a readme file so that i can upload as github project

```markdown
# Tax AI Native Platform 🚀

[![K8s](https://img.shields.io/badge/Kubernetes-v1.29-green?logo=kubernetes)](https://kubernetes.io)
[![FastAPI](https://img.shields.io/badge/FastAPI-v0.115-blue?logo=fastapi)](https://fastapi.tiangolo.com)
[![Phi-3](https://img.shields.io/badge/Phi-3-Self%20Hosted-orange?logo=huggingface)](https://huggingface.co/microsoft/Phi-3-mini-4k-instruct)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**65x faster tax calculations** with **production-grade Kubernetes architecture**. Dynamic routing between **Phi-3 vLLM** (187ms) and **Legacy Monolith** (6s) via single `/ai-tax` endpoint.

## 🎯 **Problems Solved**

| **Problem** | **Legacy (6s Monolith)** | **AI-Native Solution** |
|-------------|---------------------------|-------------------------|
| **Latency** | 6.3s per request | **187ms (65x faster)** |
| **Scalability** | Single-threaded | **K8s HPA autoscaling** |
| **Cost** | External GPT ($0.15/M tokens) | **Self-hosted Phi-3 ($0.004/M)** |
| **Complexity** | Rule explosion | **Dynamic Phi-3/Legacy routing** |

**Business Impact**: P99 <1s latency, 92% cost savings, seamless migration path.

## 🏗️ **Architecture**

```mermaid
graph TB
    Client[Client /ai-tax] -->|complexity=low| TaxAPI[tax-api<br/>FastAPI]
    Client -->|complexity=high<br/>amount>2M<br/>jurisdictions>2| TaxAPI
    
    TaxAPI -->|Phi-3 Path| Phi3VLLM[dialo-vllm<br/>Phi-3 vLLM<br/>dialoGPT-medium]
    TaxAPI -->|Legacy Path| LegacyMonolith[Legacy Engine<br/>6s Simulation]
    
    TaxAPI --> Cache[Redis<br/>tax-ai namespace]
    
    subgraph K8s ["3-Node kind Cluster"]
        TaxAPI
        Phi3VLLM
        Cache
    end
    
    HPA[HPA 50% CPU] -.-> TaxAPI
```


## 🚀 **Quick Start (5 Minutes)**

### **Prerequisites**

- Docker Desktop 4.38+
- kubectl + kind
- 8GB+ RAM (Phi-3 needs ~4Gi)


### **1. Local kind Cluster**

```bash
kind create cluster --name tax-ai-demo
```


### **2. Deploy Stack**

```bash
# Namespace + Redis
kubectl```

