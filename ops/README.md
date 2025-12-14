# Subnet2 Ops

Docker Compose setup for subnet2 evaluation infrastructure.

## Quick Start

```bash
# Copy environment file
cp .env.example .env

# Edit configuration
nano .env

# Build the Docker image first
docker compose build

# Start infrastructure
docker compose up -d

# Run migrations (after postgres is healthy)
docker compose run --rm migrations

# View logs
docker compose logs -f
```

## Local Development with Subtensor

For local development, start the local subtensor chain:

```bash
# Start local subtensor chain
docker compose -f docker-compose.localnet.yml up -d

# Configure validator to use local network
# Set in .env: SUBTENSOR_NETWORK=local

# Then start the main infrastructure
docker compose up -d
```

The local chain exposes:
- WebSocket RPC: `ws://localhost:9944`
- HTTP RPC: `http://localhost:9945`

## Build Only

To rebuild the evaluation image after code changes:

```bash
docker compose build --no-cache infra-subnet-evaluation-worker
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| infra-subnet-postgres | 5432 | Tournament state database |
| infra-subnet-redis | 6379 | Celery broker |
| infra-subnet-evaluation-worker | - | Processes evaluation tasks |
| infra-subnet-evaluation-beat | - | Schedules epoch tasks |
| infra-subnet-evaluation-api | 8001 | Read-only REST API for webapp |
| infra-subnet-validator | - | Bittensor validator neuron |

## Volumes

| Volume | Path | Description |
|--------|------|-------------|
| infra-subnet-postgres-data | /var/lib/postgresql/data | Database storage |
| infra-subnet-repos | /data/repos | Cloned miner repositories |
| infra-subnet-datasets | /data/datasets | Evaluation datasets |

## API Endpoints

The evaluation API exposes read-only endpoints for the webapp:

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/tournaments` | List tournaments with pagination |
| `GET /api/v1/tournaments/{id}` | Tournament details with submissions |
| `GET /api/v1/tournaments/{id}/submissions` | Tournament submissions |
| `GET /api/v1/tournaments/{id}/results` | Leaderboard/results |
| `GET /api/v1/tournaments/{id}/runs` | Evaluation runs |
| `GET /api/v1/miners/{hotkey}/history` | Miner participation history |
| `GET /api/v1/stats` | Overall statistics |
| `GET /health` | Health check |
| `GET /docs` | OpenAPI documentation |

## Running the Validator

### Option 1: Docker (Recommended for production)

The validator runs as a Docker container:

```bash
# Configure wallet path in .env
WALLET_PATH=~/.bittensor/wallets

# Start all services including validator
docker compose up -d
```

### Option 2: Outside Docker (Development)

Run the validator directly:

```bash
cd subnet2
python neurons/validator.py \
  --netuid 1 \
  --wallet.name validator \
  --wallet.hotkey default \
  --subtensor.network finney
```

The validator communicates with the Celery workers via Redis for task scheduling.
