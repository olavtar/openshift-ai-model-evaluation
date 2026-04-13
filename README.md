<!-- This project was developed with assistance from AI tools. -->

# Evaluate and compare LLM models for RAG with an AI Model Evaluation QuickStart

Systematically evaluate and compare LLM models for Retrieval-Augmented Generation (RAG) use cases using DeepEval metrics and verdict-driven decision logic.

## Table of Contents

- [Detailed description](#detailed-description)
  - [Architecture](#architecture)
- [Requirements](#requirements)
  - [Minimum hardware requirements](#minimum-hardware-requirements)
  - [Minimum software requirements](#minimum-software-requirements)
- [Deploy](#deploy)
  - [Prerequisites](#prerequisites)
  - [Supported Models](#supported-models)
  - [Installation Steps](#installation-steps)
  - [Local Development](#local-development)
- [Tags](#tags)

## Detailed description

See how a compliance team evaluates two candidate LLM models for a Financial Services RAG chatbot. They upload SEC and FINRA regulatory documents, run each model against the same compliance questions, and compare results -- completeness, correctness, faithfulness, and compliance accuracy scores reveal which model is safe to deploy, or whether both fail minimum quality thresholds.

"Model Evaluation helps teams move beyond subjective 'it looks good' assessments to data-driven model selection, using LLM-as-judge metrics that measure what matters for production RAG systems."

This QuickStart allows users to:

- Upload domain documents (PDFs) and build a vector knowledge base
- Run evaluations against different LLM models using DeepEval metrics
- Compare models head-to-head with disqualification gates and verdict hierarchy
- Generate evaluation questions automatically from uploaded documents
- Configure evaluation profiles with domain-specific pass/fail thresholds

### Evaluation Metrics

| Metric | What It Measures |
|--------|-----------------|
| **Faithfulness** | Is the answer grounded in retrieved context? (Detects hallucination) |
| **Answer Relevancy** | Is the answer relevant and useful for the question? |
| **Context Precision** | Did the retriever rank the right chunks highest? |
| **Context Relevancy** | Is the retrieved context relevant to the question? |
| **Completeness** | Does the answer cover all key points from the expected answer? |
| **Correctness** | Are the claims factually consistent with the expected answer? |
| **Compliance Accuracy** | Are domain-specific compliance items correctly handled? |
| **Abstention Quality** | Does the answer appropriately handle uncertainty? |

### Architecture

| Layer/Component | Technology | Purpose |
|----------------|------------|---------|
| **Frontend** | React 19 + Vite | Evaluation dashboard, model comparison, document management |
| **Routing** | TanStack Router | Type-safe file-based routing |
| **State** | TanStack Query | Server state management and caching |
| **Backend** | FastAPI | Async API for evaluation orchestration |
| **Evaluation** | DeepEval | LLM-as-judge metric scoring |
| **Database** | PostgreSQL + pgvector | Evaluation data, document embeddings, vector search |
| **Retrieval** | Hybrid (vector + keyword) | Reciprocal Rank Fusion for chunk retrieval |
| **Model Serving** | MaaS / LiteLLM | OpenAI-compatible model endpoints |
| **Build System** | Turborepo | Monorepo task orchestration |
| **Deployment** | Helm | OpenShift/Kubernetes deployment |

## Requirements

### Minimum hardware requirements

**MaaS deployment (default -- no GPU required):**

- Models are served from the RHOAI MaaS platform
- Standard compute for the API and UI workloads
- PostgreSQL with pgvector for document embeddings

**Self-hosted deployment:**

- GPU nodes for model serving (model-dependent)
- Refer to model-specific VRAM requirements

### Minimum software requirements

- OpenShift Client CLI -- `oc`
- OpenShift Cluster 4.10+ with RHOAI 3.x
- Helm CLI -- `helm` (v3.8+)
- Container registry access (for pushing images)

**For local development only:**

- Node.js 18+
- pnpm 9+
- Python 3.11+
- uv (Python package manager)
- Podman and podman-compose

## Deploy

The instructions below will deploy this QuickStart to your OpenShift environment. See the [local development](#local-development) section for running locally without OpenShift.

### Prerequisites

- Access to a MaaS endpoint with available models (or self-hosted model serving)
- MaaS API token for authentication
- Container images built and pushed to a registry

### Supported Models

This QuickStart uses three model roles:

| Role | Purpose | Examples |
|------|---------|---------|
| **Model A** | First candidate model for evaluation | `granite-3-2-8b-instruct`, `granite-4-0-h-tiny` |
| **Model B** | Second candidate model for comparison | `granite-4-0-h-tiny`, `llama-scout-17b` |
| **Judge Model** | LLM-as-judge for scoring (must differ from A and B) | `llama-scout-17b`, `Mistral-Small-24B-W8A8` |
| **Embedding Model** | Document embedding for vector search | `nomic-embed-text-v1-5`, `Nomic-embed-text-v2-moe` |

Models must be available on your MaaS endpoint or deployed self-hosted. The judge model should be different from both candidate models to avoid self-evaluation bias.

### Installation Steps

1. **Clone Repository**

```bash
git clone https://github.com/rh-ai-quickstart/model-evaluation
cd model-evaluation
```

2. **Login to OpenShift**

```bash
oc login --server="<cluster-api-endpoint>" --token="sha256~XYZ"
```

3. **Build and Push Container Images**

```bash
# Build API image
cd packages/api
podman build -f Containerfile -t model-evaluation-api:latest .

# Build UI image
cd ../ui
podman build -f Containerfile -t model-evaluation-ui:latest .

# Tag and push to your registry
podman tag model-evaluation-api:latest <registry>/model-evaluation-api:latest
podman tag model-evaluation-ui:latest <registry>/model-evaluation-ui:latest
podman push <registry>/model-evaluation-api:latest
podman push <registry>/model-evaluation-ui:latest
```

4. **Navigate to Deployment Directory**

```bash
cd deploy/helm/ai-quickstart-template
```

5. **Configure Values**

Copy the default values and configure for your environment:

```bash
cp values.yaml my-values.yaml
```

Edit `my-values.yaml` with your registry, MaaS endpoint, model names, and secrets. See the [Helm Chart README](deploy/helm/ai-quickstart-template/README.md) for all available configuration options.

At minimum, you must set:

| Parameter | Description |
|-----------|-------------|
| `global.imageRegistry` | Your container image registry |
| `models.maasEndpoint` | Your MaaS or LiteLLM endpoint URL |
| `models.modelA.name` | First candidate model name |
| `models.modelB.name` | Second candidate model name |
| `models.judgeModel` | LLM-as-judge model (must differ from A and B) |
| `models.embeddingModel` | Embedding model for vector search |
| `secrets.API_TOKEN` | MaaS authentication token |
| `secrets.POSTGRES_PASSWORD` | Database password |

6. **Deploy with Helm**

```bash
# Create namespace
oc new-project model-evaluation || oc project model-evaluation

# Install with your custom values
helm install model-evaluation . \
  --namespace model-evaluation \
  -f my-values.yaml
```

Database migrations run automatically via a Kubernetes Job on first deployment.

7. **Monitor Deployment**

```bash
oc get pods -n model-evaluation
```

Watch for all pods to reach Running status:

```
NAME                                    READY   STATUS
model-evaluation-api-xxxxx              1/1     Running
model-evaluation-ui-xxxxx               1/1     Running
model-evaluation-db-xxxxx               1/1     Running
model-evaluation-migration-xxxxx        0/1     Completed
```

8. **Verify Installation**

```bash
# Check all resources
oc get pods -n model-evaluation
oc get svc -n model-evaluation
oc get routes -n model-evaluation

# Verify API health
curl -s "$(oc get route model-evaluation-api -n model-evaluation -o jsonpath='{.spec.host}')/health/ready"
```

9. **Access the Application**

Get the route URLs:

```bash
# UI URL
oc get route model-evaluation-ui -n model-evaluation -o jsonpath='{.spec.host}'

# API URL
oc get route model-evaluation-api -n model-evaluation -o jsonpath='{.spec.host}'
```

10. **Run Your First Evaluation**

    1. Open the UI in your browser
    2. Navigate to **Documents** and upload FSI-related PDFs (SEC filings, compliance documents)
    3. Navigate to **Evaluations** and click **New Evaluation**
    4. Select a model, choose an evaluation profile (e.g., `fsi_compliance_v1`), and add questions
    5. Run the evaluation, then repeat with a different model
    6. Go to **Compare** to see the head-to-head verdict

### Upgrading

```bash
helm upgrade model-evaluation . \
  --namespace model-evaluation \
  --reuse-values \
  --set global.imageTag=v1.1.0
```

### Uninstalling

```bash
helm uninstall model-evaluation --namespace model-evaluation
oc delete project model-evaluation
```

### Local Development

For local development and testing without OpenShift:

1. **Install dependencies**:

```bash
make setup
```

2. **Configure environment**:

Copy the example and fill in your values:

```bash
cp .env.example .env
```

At minimum, set `MAAS_ENDPOINT`, `API_TOKEN`, and model names. See `.env.example` for all available variables.

3. **Start database**:

```bash
make db-start
```

4. **Run migrations**:

```bash
make db-upgrade
```

5. **Start development servers**:

```bash
make dev
```

Development URLs:

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Database | postgresql://localhost:5432 |

### Available Commands

```bash
make setup            # Install all dependencies
make dev              # Start all development servers
make build            # Build all packages
make test             # Run tests across all packages
make lint             # Check code formatting
make db-start         # Start database container
make db-stop          # Stop database container
make db-upgrade       # Run database migrations
make clean            # Clean build artifacts
```

## Project Structure

```
model-evaluation/
├── packages/
│   ├── ui/                      # React frontend
│   │   └── src/
│   │       ├── routes/          # Pages (evaluations, documents, comparison)
│   │       ├── components/      # UI components (shadcn/ui)
│   │       ├── hooks/           # TanStack Query hooks
│   │       └── services/        # API client services
│   ├── api/                     # FastAPI backend
│   │   └── src/
│   │       ├── routes/          # API endpoints
│   │       ├── services/        # Scoring, verdicts, retrieval, generation
│   │       └── profiles/        # Evaluation profiles (YAML)
│   └── db/                      # Database layer
│       ├── src/db/              # SQLAlchemy models
│       └── alembic/             # Database migrations
├── deploy/helm/                 # Helm charts for OpenShift
├── compose.yml                  # Local dev (PostgreSQL + pgvector)
└── Makefile                     # Development commands
```

### Package Documentation

- **[API README](packages/api/README.md)** -- FastAPI backend, DeepEval integration, evaluation profiles
- **[UI README](packages/ui/README.md)** -- React frontend, routing, components, hooks
- **[DB README](packages/db/README.md)** -- PostgreSQL models, pgvector, migrations
- **[Helm Chart README](deploy/helm/ai-quickstart-template/README.md)** -- Deployment configuration and values

## Tags

- **Product:** OpenShift AI
- **Use case:** Model Evaluation
- **Business challenge:** Adopt and scale AI
