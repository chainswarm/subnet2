# Local Development Setup

This guide explains how to set up a local Bittensor development environment using the `subtensor-localnet` Docker image.

## Prerequisites

- Docker installed and running
- btcli installed (`pip install bittensor-cli`)

## 1. Create Docker Volumes (Once)

Create persistent volumes to store chain data and keystore:

```bash
docker volume create subtensor_data
docker volume create subtensor_keystore
```

## 2. Run the Subtensor Local Chain

Start the local chain container with volume mounts:

```bash
docker run -d --name local_chain \
  -p 9994:9944 -p 9995:9945 \
  -v subtensor_data:/data \
  -v subtensor_keystore:/keystore \
  ghcr.io/opentensor/subtensor-localnet:devnet-ready
```

**Ports:**
- `9994` → WebSocket RPC (read operations)
- `9995` → WebSocket RPC (write operations)

## 3. Verify Chain is Running

List available subnets to verify the chain is operational:

```bash
btcli subnet list --network ws://127.0.0.1:9994
```

## 4. Create Development Wallets

Create wallets using dev URIs (alice, bob, charlie, david, eve, steve):

```bash
# Subnet owner wallet
btcli wallet create --uri alice --wallet.name subnet_local --wallet.hotkey default

# Validator wallet
btcli wallet create --uri bob --wallet.name validator_local --wallet.hotkey default

# Miner wallets
btcli wallet create --uri charlie --wallet.name miner1_local --wallet.hotkey default
btcli wallet create --uri dave --wallet.name miner2_local --wallet.hotkey default
btcli wallet create --uri eve --wallet.name miner3_local --wallet.hotkey default
```

**Note:** These URIs are pre-funded development accounts. Each has a balance for testing.

## 5. Verify Wallets

```bash
btcli wallet list --network ws://127.0.0.1:9994
```

## 6. Create the Subnet

Create a new subnet (requires TAO from the subnet wallet):

```bash
btcli subnet create \
  --subnet-name chain-insights \
  --wallet.name subnet \
  --network ws://127.0.0.1:9995
```

## 7. Start the Subnet

Activate the subnet (netuid 2 is typically the first user-created subnet):

```bash
btcli subnet start --netuid 2 \
  --wallet.name subnet_local \
  --network ws://127.0.0.1:9995
```

## 8. Register Participants

Register the validator and miners on the subnet:

```bash
# Register validator
btcli subnets register --netuid 2 \
  --wallet-name validator_local \
  --hotkey default \
  --network ws://127.0.0.1:9995

# Register miners
btcli subnets register --netuid 2 \
  --wallet-name miner1_local \
  --hotkey default \
  --network ws://127.0.0.1:9995

btcli subnets register --netuid 2 \
  --wallet-name miner2_local \
  --hotkey default \
  --network ws://127.0.0.1:9995

btcli subnets register --netuid 2 \
  --wallet-name miner3_local \
  --hotkey default \
  --network ws://127.0.0.1:9995
```

## 9. Run Miners

Start each miner on a different port:

```bash
# Terminal 1 - Miner 1
python neurons/miner.py \
  --wallet.name miner1_local \
  --wallet.hotkey default \
  --subtensor.network ws://127.0.0.1:9995 \
  --axon.port 8901 \
  --netuid 2

# Terminal 2 - Miner 2
python neurons/miner.py \
  --wallet.name miner2_local \
  --wallet.hotkey default \
  --subtensor.network ws://127.0.0.1:9995 \
  --axon.port 8902 \
  --netuid 2

# Terminal 3 - Miner 3
python neurons/miner.py \
  --wallet.name miner3_local \
  --wallet.hotkey default \
  --subtensor.network ws://127.0.0.1:9995 \
  --axon.port 8903 \
  --netuid 2
```

### With Submission Configuration

To participate in evaluation tournaments, add submission parameters:

```bash
python neurons/miner.py \
  --wallet.name miner1_local \
  --wallet.hotkey default \
  --subtensor.network ws://127.0.0.1:9995 \
  --axon.port 8901 \
  --netuid 2 \
  --submission.repository_url https://github.com/youruser/analyzer.git \
  --submission.commit_hash abc123
```

## 10. Run Validator

Start the validator:

```bash
python neurons/validator.py \
  --wallet.name validator_local \
  --wallet.hotkey default \
  --subtensor.network ws://127.0.0.1:9995 \
  --netuid 2
```

## 11. Verify Subnet Status

Check the subnet metagraph:

```bash
btcli subnet show --netuid 2 --network ws://127.0.0.1:9995
```

## 12. Add Stake (Optional)

Add stake to the validator to increase its influence:

```bash
btcli stake add --netuid 2 \
  --wallet-name validator_local \
  --hotkey default \
  --partial \
  --network ws://127.0.0.1:9995
```

Check validator overview:

```bash
btcli wallet overview --wallet.name validator_local
 --network ws://127.0.0.1:9995
```

---

## Quick Reference

### Ports

| Port | Description |
|------|-------------|
| 9994 | Subtensor RPC (read) |
| 9995 | Subtensor RPC (write) |
| 8901-8903 | Miner axon ports |

### Dev Wallet URIs

| URI | Pre-funded Account |
|-----|-------------------|
| alice | Subnet owner |
| bob | Validator |
| charlie | Miner 1 |
| dave | Miner 2 |
| eve | Miner 3 |
| steve | Miner 4 (spare) |

### Useful Commands

```bash
# Stop the local chain
docker stop local_chain

# Start the local chain (after stopping)
docker start local_chain

# View chain logs
docker logs -f local_chain

# Remove everything and start fresh
docker rm -f local_chain
docker volume rm subtensor_data subtensor_keystore
```

---

## Running with Docker Compose (Recommended)

Using Docker Compose is the recommended approach as it automatically manages persistent volumes for chain data.

```bash
cd subnet2/ops

# Start the local chain with persistent volumes
docker compose -f docker-compose.localnet.yml up -d

# Check logs
docker compose -f docker-compose.localnet.yml logs -f local-chain
```

**Note:** Docker Compose automatically creates named volumes (`subtensor-data` and `subtensor-keystore`) that persist your chain data across restarts.

### Ports (Docker Compose)

| Port | Description |
|------|-------------|
| 9944 | Subtensor RPC (read) |
| 9945 | Subtensor RPC (write) |

When using Docker Compose, use these ports:
```bash
btcli subnet list --network ws://127.0.0.1:9944
```

### Stop and Start

```bash
# Stop (data persists)
docker compose -f docker-compose.localnet.yml down

# Start again (data is preserved)
docker compose -f docker-compose.localnet.yml up -d

# Remove everything including volumes (fresh start)
docker compose -f docker-compose.localnet.yml down -v
```

See [`README.md`](README.md) for more details on the Docker Compose setup.
