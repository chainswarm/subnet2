# Subnet2 Ops

Docker Compose setup for subnet2 evaluation infrastructure.

## Deployment Environments

This project provides three Docker Compose configurations for different deployment scenarios:

### 1. Development (Base Configuration)
- **File**: [`docker-compose.yml`](docker-compose.yml)
- **Network**: Configurable (default: finney)
- **Tournament Schedule**: Manual mode (short cycles for testing)
- **Purpose**: Local development and testing

### 2. Testnet Deployment
- **File**: [`docker-compose.testnet.yml`](docker-compose.testnet.yml)
- **Network**: `test` (Bittensor testnet)
- **Tournament Schedule**: Daily automated (12-hour cycles)
- **Purpose**: Production-like testing with accelerated tournament cycles

### 3. Mainnet Deployment
- **File**: [`docker-compose.mainnet.yml`](docker-compose.mainnet.yml)
- **Network**: `finney` (Bittensor mainnet)
- **Tournament Schedule**: Daily automated (6-day cycles)
- **Purpose**: Full production deployment

## Quick Start

### Development (Local)

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

### Testnet Deployment

```bash
# Copy and configure testnet environment
cp .env.example .env.testnet
nano .env.testnet  # Configure for testnet

# Build the Docker image
docker compose -f docker-compose.yml build

# Start testnet infrastructure
docker compose -f docker-compose.yml -f docker-compose.testnet.yml up -d

# Run migrations
docker compose -f docker-compose.yml -f docker-compose.testnet.yml run --rm migrations

# View logs
docker compose -f docker-compose.yml -f docker-compose.testnet.yml logs -f
```

**Testnet Tournament Timing** (12-hour cycle):
- Submission phase: 1 hour
- Epoch count: 3 epochs × 3 hours = 9 hours
- Total tournament time: ~10 hours
- Daily automated tournaments

### Mainnet Deployment

```bash
# Copy and configure mainnet environment
cp .env.example .env.mainnet
nano .env.mainnet  # Configure for mainnet with SECURE credentials

# Build the Docker image
docker compose -f docker-compose.yml build

# Start mainnet infrastructure
docker compose -f docker-compose.yml -f docker-compose.mainnet.yml up -d

# Run migrations
docker compose -f docker-compose.yml -f docker-compose.mainnet.yml run --rm migrations

# Monitor services
docker compose -f docker-compose.yml -f docker-compose.mainnet.yml logs -f
```

**Mainnet Tournament Timing** (6-day cycle):
- Submission phase: 24 hours
- Epoch count: 5 epochs × 24 hours = 120 hours
- Total tournament time: 6 days
- Daily automated tournaments (multiple concurrent)

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
| infra-subnet-flower | 5555 | Celery task monitoring UI |

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

## Environment Configuration Reference

### Key Environment Variables by Deployment

| Variable | Development | Testnet | Mainnet |
|----------|-------------|---------|---------|
| `SUBTENSOR_NETWORK` | finney/local | test | finney |
| `TOURNAMENT_SCHEDULE_MODE` | manual | daily | daily |
| `TOURNAMENT_SUBMISSION_DURATION_SECONDS` | 120 | 3600 | 86400 |
| `TOURNAMENT_EPOCH_COUNT` | 3 | 3 | 5 |
| `TOURNAMENT_EPOCH_DURATION_SECONDS` | 180 | 10800 | 86400 |
| `TOURNAMENT_NETWORKS` | torus | torus,bittensor | torus,bittensor,ethereum |
| `WORKER_CONCURRENCY` | 2 | 2-4 | 4-8 |
| `LOG_LEVEL` | INFO | INFO | WARNING |

### Security Considerations

**For Production (Mainnet/Testnet)**:
1. Use strong, unique passwords (32+ characters)
2. Never commit `.env.mainnet` or `.env.testnet` to version control
3. Restrict network access with firewall rules
4. Enable HTTPS/TLS for exposed services
5. Regularly backup database and wallet keys
6. Monitor resource usage and set up alerts
7. Keep Docker images and dependencies updated

## Monitoring

Access Flower (Celery monitoring) at `http://localhost:5555`:
- Username/Password configured via `FLOWER_USER` and `FLOWER_PASSWORD`
- View active tasks, worker status, and task history
- Monitor queue lengths and task execution times

## Troubleshooting

### Services won't start
```bash
# Check service status
docker compose ps

# View detailed logs
docker compose logs infra-subnet-postgres
docker compose logs infra-subnet-evaluation-worker
```

### Reset everything
```bash
# Stop all services
docker compose down

# Remove volumes (WARNING: deletes all data)
docker compose down -v

# Rebuild and restart
docker compose build --no-cache
docker compose up -d
docker compose run --rm migrations
```

### Database migrations fail
```bash
# Check PostgreSQL is healthy
docker compose logs infra-subnet-postgres

# Manually run migrations with verbose output
docker compose run --rm migrations alembic upgrade head
```

## Production Checklist

Before deploying to mainnet:

- [ ] Configure secure passwords in `.env.mainnet`
- [ ] Verify Bittensor wallet is funded and registered
- [ ] Set correct `NETUID` for your subnet
- [ ] Configure resource limits appropriately
- [ ] Set up external monitoring (uptime, disk space, memory)
- [ ] Configure automated backups (database, wallet keys)
- [ ] Test disaster recovery procedures
- [ ] Enable firewall rules
- [ ] Document runbook for common operations
- [ ] Set up log aggregation and alerting
