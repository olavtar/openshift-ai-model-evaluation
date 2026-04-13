# OpenShift AI Model Evaluation QuickStart

Helm chart for deploying the OpenShift AI Model Evaluation platform, which enables easy comparison of LLM models using RAG-specific evaluation metrics.

## Overview

This chart deploys a complete model evaluation stack:

- **API service** (FastAPI backend)
- **UI service** (React frontend)
- **PostgreSQL database** with pgvector extension
- **RAG pipeline** for document processing and retrieval
- **Evaluation framework** using DeepEval metrics (faithfulness, answer relevancy, contextual precision)

Supports two deployment modes:
1. **MaaS (default)**: Use Red Hat OpenShift AI MaaS platform models (zero GPU required)
2. **Self-hosted**: Deploy models on-cluster with GPU resources

## Prerequisites

- OpenShift 4.10+ or Kubernetes 1.24+
- Helm 3.8+
- `oc` or `kubectl` CLI
- Access to container registry (default: quay.io/rh-ai-quickstart)
- For MaaS mode: Valid RHOAI MaaS API token
- For self-hosted mode: GPU-enabled nodes with NVIDIA device plugin

## Quick Start

### MaaS Deployment (Zero GPU)

```bash
# Create namespace
oc new-project model-evaluation

# Install with MaaS endpoint
helm install model-eval . \
  --set secrets.API_TOKEN="your-maas-api-token" \
  --set models.maasEndpoint="https://maas.apps.prod.rhoai.rh-aiservices-bu.com/"
```

Access the UI at the Route created in your namespace:

```bash
oc get route model-evaluation-ui
```

### Self-Hosted Deployment (GPU Required)

```bash
# Enable llm-service subchart for on-cluster model serving
helm install model-eval . \
  --set llm-service.enabled=true \
  --set models.modelA.deploymentMode=self-hosted \
  --set models.modelB.deploymentMode=self-hosted
```

## Configuration

### Key Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `global.imageRegistry` | Container registry | `quay.io` |
| `global.imageRepository` | Image repository | `rh-ai-quickstart` |
| `global.imageTag` | Image tag | `latest` |
| `models.maasEndpoint` | RHOAI MaaS endpoint URL | `https://maas.apps.prod.rhoai.rh-aiservices-bu.com/` |
| `models.modelA.name` | First comparison model | `granite-3.1-8b-instruct` |
| `models.modelA.deploymentMode` | Deployment mode for model A | `maas` |
| `models.modelB.name` | Second comparison model | `meta-llama/llama-3.1-8b-instruct` |
| `models.modelB.deploymentMode` | Deployment mode for model B | `maas` |
| `models.embeddingModel.name` | Embedding model for RAG | `nomic-embed-text-v1.5` |
| `models.judgeModel.name` | Judge model for evaluation | `granite-3.1-8b-instruct` |
| `secrets.API_TOKEN` | MaaS API token (required for MaaS mode) | `""` |
| `secrets.POSTGRES_PASSWORD` | Database password | Auto-generated |
| `routes.enabled` | Enable OpenShift Routes | `true` |
| `routes.tls.enabled` | Enable TLS on routes | `true` |
| `database.persistence.size` | PVC size for database | `10Gi` |
| `api.replicas` | API pod replicas | `1` |
| `ui.replicas` | UI pod replicas | `1` |

### Full Values Reference

See [values.yaml](values.yaml) for complete configuration options.

## Deployment Modes

### MaaS (Model as a Service)

**Recommended for getting started**. Uses RHOAI MaaS platform to serve models remotely.

**Benefits:**
- No GPU resources required
- Curated model catalog
- Zero infrastructure management
- Lower cost for experimentation

**Configuration:**

```yaml
models:
  maasEndpoint: "https://maas.apps.prod.rhoai.rh-aiservices-bu.com/"
  modelA:
    name: "granite-3.1-8b-instruct"
    deploymentMode: maas
  modelB:
    name: "meta-llama/llama-3.1-8b-instruct"
    deploymentMode: maas

secrets:
  API_TOKEN: "your-api-token-here"
```

**Getting a MaaS API Token:**
Contact your RHOAI administrator or see RHOAI MaaS documentation.

### Self-Hosted

Deploy models directly on your OpenShift cluster. Required for:
- Larger models (70B+)
- Custom fine-tuned models
- Air-gapped environments
- Strict data residency requirements

**Prerequisites:**
- GPU nodes in your cluster
- NVIDIA GPU Operator installed
- Sufficient GPU memory for chosen models

**Configuration:**

```yaml
llm-service:
  enabled: true
  # See llm-service chart documentation for GPU configuration

models:
  modelA:
    name: "your-model-name"
    deploymentMode: self-hosted
  modelB:
    name: "your-other-model"
    deploymentMode: self-hosted
```

## Model Configuration

### Available Models (MaaS)

Common models available via RHOAI MaaS:

| Model | Size | Use Case |
|-------|------|----------|
| `granite-3.1-8b-instruct` | 8B | General purpose, fast responses |
| `meta-llama/llama-3.1-8b-instruct` | 8B | Balanced performance |
| `meta-llama/llama-3.1-70b-instruct` | 70B | High accuracy (requires MaaS) |

### Embedding Models

| Model | Dimensions | Use Case |
|-------|------------|----------|
| `nomic-embed-text-v1.5` | 768 | Default, good balance |
| `sentence-transformers/all-MiniLM-L6-v2` | 384 | Smaller, faster |

### Judge Models

The judge model evaluates outputs using DeepEval metrics. Recommended:
- `granite-3.1-8b-instruct` (default, cost-effective)
- `meta-llama/llama-3.1-70b-instruct` (higher accuracy, higher cost)

### Example: Mixed Deployment

```yaml
models:
  modelA:
    name: "granite-3.1-8b-instruct"
    deploymentMode: maas
  modelB:
    name: "custom-fine-tuned-model"
    deploymentMode: self-hosted
  embeddingModel:
    name: "nomic-embed-text-v1.5"
    deploymentMode: maas
  judgeModel:
    name: "granite-3.1-8b-instruct"
    deploymentMode: maas
```

## TLS and Routes

### Default Route Configuration

The chart creates two OpenShift Routes with TLS edge termination:

```yaml
routes:
  enabled: true
  tls:
    enabled: true
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
  timeout: 600s
```

### Custom Hostname

```yaml
routes:
  sharedHost: "model-eval.apps.your-cluster.com"
```

### Disable Routes (Use Ingress Instead)

```yaml
routes:
  enabled: false
```

Then create your own Ingress resources.

## Database

### Persistence

By default, the database uses a 10Gi PersistentVolumeClaim:

```yaml
database:
  persistence:
    enabled: true
    size: 10Gi
    storageClassName: ""  # Use default storage class
```

### External Database

To use an external PostgreSQL database with pgvector:

```yaml
database:
  enabled: false

secrets:
  DATABASE_URL: "postgresql://user:pass@external-db:5432/dbname"
```

**Requirements:**
- PostgreSQL 14+
- `pgvector` extension installed

### Backups

The chart does not include automated backups. For production:

1. Use OpenShift Data Foundation backup capabilities
2. Configure pg_dump cron jobs
3. Use a managed PostgreSQL service with built-in backups

## Upgrading

```bash
# Update values
helm upgrade model-eval . \
  --set global.imageTag=v1.2.0 \
  --reuse-values

# Database migrations run automatically via Job
# Check migration status
oc get job model-evaluation-migration
```

## Uninstalling

```bash
helm uninstall model-eval

# Optional: Delete PVCs (data will be lost)
oc delete pvc -l app.kubernetes.io/instance=model-eval
```

## Troubleshooting

### API Pod Not Ready

```bash
# Check logs
oc logs -l app.kubernetes.io/component=api

# Check database connection
oc exec -it deployment/model-evaluation-api -- env | grep DATABASE_URL
```

### Migration Job Fails

```bash
# Check migration logs
oc logs job/model-evaluation-migration

# Manually run migration
oc run -it migration-debug --image=quay.io/rh-ai-quickstart/model-evaluation-api:latest \
  --env-from=secret/model-evaluation-secrets \
  --command -- alembic upgrade head
```

### MaaS Authentication Errors

```bash
# Verify API token is set
oc get secret model-evaluation-secrets -o jsonpath='{.data.API_TOKEN}' | base64 -d

# Test MaaS endpoint
curl -H "Authorization: Bearer $API_TOKEN" \
  https://maas.apps.prod.rhoai.rh-aiservices-bu.com/v1/models
```

### UI Shows Blank Page

```bash
# Check UI logs
oc logs -l app.kubernetes.io/component=ui

# Verify API route is accessible from UI pod
oc exec -it deployment/model-evaluation-ui -- curl http://model-evaluation-api:8000/health/live
```

### Self-Hosted Model Issues

```bash
# Check GPU availability
oc describe node -l nvidia.com/gpu.present=true

# Check llm-service logs
oc logs -l app.kubernetes.io/name=llm-service

# Verify model loaded
oc exec -it deployment/llm-service -- curl localhost:8080/v1/models
```

### Database Connection Timeouts

```bash
# Check database pod status
oc get pod -l app.kubernetes.io/component=database

# Check PVC binding
oc get pvc

# Check database logs
oc logs -l app.kubernetes.io/component=database
```

## Known Issues

- Chart directory name (`ai-quickstart-template`) does not match `Chart.yaml` name (`model-evaluation`). This is a cosmetic issue and does not affect functionality.

## Support

For issues and questions:
- GitHub Issues: https://github.com/rh-ai-quickstart/model-evaluation
- Red Hat Support: https://access.redhat.com/support

## License

Apache 2.0
