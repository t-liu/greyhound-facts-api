# Greyhound Facts API

A production-grade serverless API serving facts about Greyhound dogs.

## Architecture

```
Public Users → API Gateway → AWS Lambda (FastAPI + Mangum) → DynamoDB
                                                            → Secrets Manager
```

**Stack:** Python 3.13 · FastAPI · Pydantic v2 · Mangum · AWS CDK · DynamoDB · GitHub Actions

## Project Structure

```
greyhound-facts-api/
├── app/                          # Application source
│   ├── api/                      # Route handlers
│   │   ├── admin.py              # Admin CRUD endpoints
│   │   └── facts.py              # Public read endpoints + health
│   ├── core/                     # Cross-cutting concerns
│   │   ├── auth.py               # X-API-Key authentication
│   │   ├── config.py             # pydantic-settings config
│   │   ├── exceptions.py         # Exception handling
│   │   ├── logging.py            # Structured JSON logging
│   │   ├── middleware.py         # Request-ID middleware
│   │   └── request_id.py         # UUID generator
│   ├── models/                   # Pydantic request/response models
│   │   ├── error.py
│   │   ├── request.py
│   │   └── response.py
│   ├── repositories/             # Data access layer
│   │   └── dynamodb_repository.py
│   ├── services/                 # Business logic
│   │   └── fact_service.py
│   ├── lambda_handler.py         # Mangum Lambda wrapper
│   ├── main.py                   # FastAPI application factory
│   └── requirements.txt          # Production dependencies
├── infra/                        # AWS CDK infrastructure
│   ├── app.py                    # CDK app entry point
│   └── stacks/
│       ├── api_stack.py          # Lambda + API Gateway + warm-up
│       ├── data_stack.py         # DynamoDB table
│       ├── observability_stack.py # Logs, alarms, dashboard
│       └── security_stack.py     # Secrets Manager + IAM
├── scripts/
│   └── seed.py                   # Database seeding script
├── tests/
│   ├── api/                      # API integration tests
│   ├── integration/              # Repository integration tests
│   ├── unit/                     # Unit tests
│   └── conftest.py               # Shared fixtures
├── .github/workflows/            # CI/CD pipelines
├── pyproject.toml                # Project metadata & tool config
├── requirements-dev.txt          # Dev dependencies
└── requirements-infra.txt        # CDK dependencies
```

## Endpoints

### Public

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/v1/health` | Health check |
| `GET` | `/v1/facts/random` | Retrieve a random fact |
| `GET` | `/v1/facts/{id}` | Retrieve a fact by ID |

### Admin (requires `X-API-Key` header)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/admin/facts` | Create a fact |
| `PUT` | `/v1/admin/facts/{id}` | Update a fact |
| `DELETE` | `/v1/admin/facts/{id}` | Delete a fact |

## Local Development

### Prerequisites

- Python 3.13+
- AWS CLI configured
- Node.js (for CDK)

### Setup

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r app/requirements.txt
pip install -r requirements-dev.txt
pip install -r requirements-infra.txt
cp .env.example .env
```

### Run locally

```bash
python -m uvicorn app.main:app --reload
```

API docs available at `http://localhost:8000/v1/docs`

### Environment Variables

See `.env.example` for all available configuration options.

## Testing

```bash
pytest --cov=app --cov-report=term-missing
```

Minimum coverage: **90%**

## Seeding Data

```bash
python scripts/seed.py
```

## Infrastructure

Managed with AWS CDK (Python):

```bash
cd infra
pip install -r requirements.txt
cdk bootstrap aws://ACCOUNT_ID/REGION
cdk synth --all --app "python app.py" -c env=ENV
# If you are inside a virtual environment:
cdk deploy --all --app "../.venv/bin/python app.py" -c env=dev -c account=ACCOUNT -c region=REGION
# If you are NOT inside a virtual environment:
cdk deploy --all --app "python app.py" -c env=ENV
```

### CDK Stacks

| Stack | Resources |
|-------|-----------|
| `data_stack` | DynamoDB table, seed data |
| `security_stack` | Secrets Manager, IAM roles |
| `api_stack` | Lambda, API Gateway, EventBridge warm-up |
| `observability_stack` | CloudWatch log groups, alarms |

## CI/CD

- **PR checks:** lint (ruff), type check (mypy), tests (pytest), security (bandit, pip-audit, gitleaks)
- **Main branch:** build → deploy dev → smoke tests
- **Release:** manual approval → deploy prod → smoke tests → CloudWatch validation

## Architecture Decisions

See the [Architecture Decision Records](./docs/ADRs.md) for key design choices including:
- No list-all endpoint (avoids DynamoDB Scan)
- Fixed `METADATA` sort key for single-table design extensibility
- Index-based O(1) random selection
- `/v1/` versioning from day one

## Cold Start Behavior

Python Lambda cold starts are typically 1–3 seconds. Mitigated by:
1. EventBridge scheduled warm-up ping every 5 minutes (business hours)
2. Minimal production dependencies
