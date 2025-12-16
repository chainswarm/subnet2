# Subnet2 Ops

Docker Compose setup for subnet2 evaluation infrastructure.

## Architecture Overview

The Docker Compose setup is organized into SEPARATE components that can be run independently:

- **[`docker-compose.yml`](docker-compose.yml)**: ALL application services (PostgreSQL, Redis, Celery, Validator, API, Flower, Migrations)
- **[`docker-compose.testnet.yml`](docker-compose.testnet.yml)**: ONLY Bittensor testnet-lite subtensor node
- **[`docker-compose.mainnet.yml`](docker-compose.mainnet.yml)**: ONLY Bittensor mainnet-lite subtensor node
- **[`docker-compose.localnet.yml`](docker-compose.localnet.yml)**: ONLY local development subtensor node

**Key Principle**: Subtensor nodes run SEPARATELY from application services. Configure connection via `.env` file.

## Deployment Environments

### 1. Development (Local)
- **Application**: [`docker-compose.yml`](docker-compose.yml)
- **Subtensor Node**: Optional - can use remote endpoints or local node
- **Network**: Configurable via `SUBTENSOR_NETWORK` in `.env` (default: finney remote)
- **Tournament Schedule**: Manual mode (short cycles for testing)
- **Purpose**: Local development and testing

### 2. Testnet Deployment
- **Application**: [`docker-compose.yml`](docker-compose.yml) with testnet `.env` config
- **Subtensor Node**: [`docker-compose.testnet.yml`](docker-compose.testnet.yml) (run separately)
- **Connection**: `SUBTENSOR_NETWORK=ws://testnet-lite:9944` in `.env`
- **Purpose**: Production-like testing with accelerated tournament cycles

### 3. Mainnet Deployment
- **Application**: [`docker-compose.yml`](docker-compose.yml) with mainnet `.env` config
- **Subtensor Node**: [`docker-compose.mainnet.yml`](docker-compose.mainnet.yml) (run separately)
- **Connection**: `SUBTENSOR_NETWORK=ws://mainnet-lite:9944` in `.env`
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

**IMPORTANT**: Subtensor node and application services run SEPARATELY.

```bash
# Step 1: Start the testnet subtensor node (separate terminal/session)
docker compose -f ops/docker-compose.testnet.yml up -d

# Wait for node to sync (30-60 minutes)
docker compose -f ops/docker-compose.testnet.yml logs -f testnet-lite

# Step 2: Configure application environment
cp ops/.env.example ops/.env.testnet
nano ops/.env.testnet
# Set: SUBTENSOR_NETWORK=ws://testnet-lite:9944
# Set: POSTGRES_DB=validator_testnet
# Set: POSTGRES_USER=validator_testnet
# Set: POSTGRES_PASSWORD=<strong-password>
# Set: TOURNAMENT_SCHEDULE_MODE=daily
# Set: TOURNAMENT_SUBMISSION_DURATION_SECONDS=3600        # 1 hour
# Set: TOURNAMENT_EPOCH_COUNT=3
# Set: TOURNAMENT_EPOCH_DURATION_SECONDS=10800             # 3 hours
# Set: TOURNAMENT_NETWORKS=torus,bittensor

# Step 3: Build application Docker image
docker compose -f ops/docker-compose.yml build

# Step 4: Start application services (separate from subtensor)
docker compose -f ops/docker-compose.yml --env-file ops/.env.testnet up -d

# Step 5: Run migrations
docker compose -f ops/docker-compose.yml --env-file ops/.env.testnet run --rm migrations

# Step 6: Monitor both separately
docker compose -f ops/docker-compose.testnet.yml logs -f testnet-lite
docker compose -f ops/docker-compose.yml logs -f
```

**Testnet Tournament Timing** (12-hour cycle):
- Submission phase: 1 hour
- Epoch count: 3 epochs × 3 hours = 9 hours
- Total tournament time: ~10 hours
- Daily automated tournaments

**Subtensor Node** (runs separately):
- File: `docker-compose.testnet.yml`
- Service: `testnet-lite`
- Endpoint: `ws://testnet-lite:9944`
- Sync time: 30-60 minutes

### Mainnet Deployment

**CRITICAL**: Subtensor node and application services run SEPARATELY. Use STRONG passwords for production!

```bash
# Step 1: Start the mainnet subtensor node (separate terminal/session)
docker compose -f ops/docker-compose.mainnet.yml up -d

# Wait for node to sync (2-4 hours) - MUST COMPLETE BEFORE STARTING VALIDATOR!
docker compose -f ops/docker-compose.mainnet.yml logs -f mainnet-lite

# Step 2: Configure application environment (SECURE passwords!)
cp ops/.env.example ops/.env.mainnet
nano ops/.env.mainnet
# Set: SUBTENSOR_NETWORK=ws://mainnet-lite:9944
# Set: POSTGRES_DB=validator_mainnet
# Set: POSTGRES_USER=validator_mainnet
# Set: POSTGRES_PASSWORD=<STRONG-32-char-random-password>
# Set: FLOWER_USER=<secure-username>
# Set: FLOWER_PASSWORD=<STRONG-32-char-random-password>
# Set: WALLET_NAME=<your-validator-wallet>
# Set: WALLET_HOTKEY=<your-hotkey>
# Set: NETUID=<your-subnet-id>
# Set: TOURNAMENT_SCHEDULE_MODE=daily
# Set: TOURNAMENT_SUBMISSION_DURATION_SECONDS=86400        # 24 hours
# Set: TOURNAMENT_EPOCH_COUNT=5
# Set: TOURNAMENT_EPOCH_DURATION_SECONDS=86400             # 24 hours
# Set: TOURNAMENT_NETWORKS=torus,bittensor,ethereum
# Set: LOG_LEVEL=WARNING

# Step 3: Build application Docker image
docker compose -f ops/docker-compose.yml build

# Step 4: Start application services (AFTER node is synced!)
docker compose -f ops/docker-compose.yml --env-file ops/.env.mainnet up -d

# Step 5: Run migrations
docker compose -f ops/docker-compose.yml --env-file ops/.env.mainnet run --rm migrations

# Step 6: Monitor both separately
docker compose -f ops/docker-compose.mainnet.yml logs -f mainnet-lite
docker compose -f ops/docker-compose.yml logs -f
```

**Mainnet Tournament Timing** (6-day cycle):
- Submission phase: 24 hours
- Epoch count: 5 epochs × 24 hours = 120 hours
- Total tournament time: 6 days
- Daily automated tournaments (multiple concurrent)

**Subtensor Node** (runs separately):
- File: `docker-compose.mainnet.yml`
- Service: `mainnet-lite`
- Endpoint: `ws://mainnet-lite:9944`
- Sync time: 2-4 hours (must complete first!)

## Local Development with Local Subtensor

For local development with a local blockchain:

```bash
# Step 1: Start local subtensor chain (separate)
docker compose -f ops/docker-compose.localnet.yml up -d

# Step 2: Configure .env to connect to local node
nano ops/.env
# Set: SUBTENSOR_NETWORK=ws://local-subtensor:9944

# Step 3: Start application services
docker compose -f ops/docker-compose.yml up -d

# Step 4: Run migrations
docker compose -f ops/docker-compose.yml run --rm migrations
```

**Local Node Endpoints**:
- From Docker network: `ws://local-subtensor:9944`
- From host: `ws://localhost:9944`

**Note**: See [`LOCAL_DEVELOPMENT.md`](LOCAL_DEVELOPMENT.md) for wallet setup and subnet creation.

## Build Only

To rebuild the evaluation image after code changes:

```bash
docker compose build --no-cache infra-subnet-evaluation-worker
```

## Services

### Application Services (Base Configuration)

| Service | Port | Description |
|---------|------|-------------|
| infra-subnet-postgres | 5432 | Tournament state database |
| infra-subnet-redis | 6379 | Celery broker |
| infra-subnet-evaluation-worker | - | Processes evaluation tasks |
| infra-subnet-evaluation-beat | - | Schedules epoch tasks |
| infra-subnet-evaluation-api | 8001 | Read-only REST API for webapp |
| infra-subnet-validator | - | Bittensor validator neuron |
| infra-subnet-flower | 5555 | Celery task monitoring UI |
| migrations | - | Database migration runner (one-time) |

### Subtensor Nodes (Network-Specific)

| Service | Config File | Network | Endpoint |
|---------|-------------|---------|----------|
| local-subtensor | docker-compose.localnet.yml | Local development | ws://localhost:9944 |
| testnet-lite | docker-compose.testnet.yml | Bittensor testnet | ws://testnet-lite:9944 |
| mainnet-lite | docker-compose.mainnet.yml | Bittensor mainnet | ws://mainnet-lite:9944 |

## Volumes

| Volume | Path | Description |
|--------|------|-------------|
| infra-subnet-postgres-data | /var/lib/postgresql/data | Database storage |
| infra-subnet-repos | /data/repos | Cloned miner repositories |
| infra-subnet-datasets | /data/datasets | Evaluation datasets |
| testnet-lite-volume | /data | Testnet blockchain data |
| mainnet-lite-volume | /data | Mainnet blockchain data |
| subtensor-data | /data | Localnet blockchain data |
| subtensor-keystore | /keystore | Localnet keystore |

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
| `SUBTENSOR_NETWORK` | finney/local | ws://testnet-lite:9944 | ws://mainnet-lite:9944 |
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

### Application services won't start
```bash
# Check service status
docker compose -f ops/docker-compose.yml ps

# View detailed logs
docker compose -f ops/docker-compose.yml logs infra-subnet-postgres
docker compose -f ops/docker-compose.yml logs infra-subnet-evaluation-worker
```

### Subtensor node won't sync
```bash
# Check testnet node logs
docker compose -f ops/docker-compose.testnet.yml logs testnet-lite

# Check mainnet node logs
docker compose -f ops/docker-compose.mainnet.yml logs mainnet-lite

# Common issues:
# - Port 30333 blocked by firewall
# - Network connectivity to bootnodes
# - Insufficient disk space
# - Initial sync takes time (30-60 min testnet, 2-4 hours mainnet)
```

### Validator can't connect to subtensor
```bash
# Verify both services are on 'subnet' network
docker network inspect subnet

# Check subtensor node is healthy
docker compose -f ops/docker-compose.testnet.yml ps
# or
docker compose -f ops/docker-compose.mainnet.yml ps

# Check validator logs
docker compose -f ops/docker-compose.yml logs infra-subnet-validator

# Verify SUBTENSOR_NETWORK setting in .env
grep SUBTENSOR_NETWORK ops/.env
```

### Reset everything
```bash
# Stop application services
docker compose -f ops/docker-compose.yml down

# Stop subtensor node
docker compose -f ops/docker-compose.testnet.yml down
# or
docker compose -f ops/docker-compose.mainnet.yml down

# Remove all volumes (WARNING: deletes all data including blockchain sync)
docker compose -f ops/docker-compose.yml down -v
docker compose -f ops/docker-compose.testnet.yml down -v

# Rebuild and restart
docker compose -f ops/docker-compose.yml build --no-cache
docker compose -f ops/docker-compose.testnet.yml up -d  # Wait for sync!
docker compose -f ops/docker-compose.yml up -d
docker compose -f ops/docker-compose.yml run --rm migrations
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
