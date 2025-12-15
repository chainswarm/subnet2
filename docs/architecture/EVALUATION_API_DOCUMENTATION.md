# Evaluation API Documentation & Dashboard Design

## Overview

The Evaluation API provides read-only access to tournament evaluation data for the Subnet network. This document describes the available endpoints, their use cases for a tournament dashboard UI, and UI mockup proposals.

---

## API Endpoints Summary

### Base URL
```
/api/v1
```

### Health Check

| Method | Endpoint | Description | Tags |
|--------|----------|-------------|------|
| GET | `/health` | Service health check and status | health |

### Tournaments

| Method | Endpoint | Description | Query Parameters |
|--------|----------|-------------|------------------|
| GET | `/api/v1/tournaments` | List all tournaments | `status`, `netuid`, `limit`, `offset` |
| GET | `/api/v1/tournaments/{tournament_id}` | Get tournament details with submissions & results | - |
| GET | `/api/v1/tournaments/{tournament_id}/submissions` | List tournament submissions | `status` |
| GET | `/api/v1/tournaments/{tournament_id}/results` | Get tournament leaderboard/rankings | - |
| GET | `/api/v1/tournaments/{tournament_id}/runs` | Get evaluation runs | `epoch_number`, `network`, `status`, `limit`, `offset` |

### Miners

| Method | Endpoint | Description | Query Parameters |
|--------|----------|-------------|------------------|
| GET | `/api/v1/miners/{hotkey}/history` | Get miner's tournament history and stats | - |

### Statistics

| Method | Endpoint | Description | Query Parameters |
|--------|----------|-------------|------------------|
| GET | `/api/v1/stats` | Get global aggregate statistics | - |

---

## Endpoint Details

### GET /api/v1/stats

Returns aggregate statistics across all tournaments.

**Response Schema:**
```json
{
  "active_tournaments": 3,
  "completed_tournaments": 12,
  "total_miners": 127,
  "total_submissions": 452,
  "total_runs_completed": 2451,
  "average_pattern_recall": 0.847,
  "baseline_beat_rate": 0.673
}
```

**Dashboard Usage:** KPI cards on dashboard home page.

---

### GET /api/v1/tournaments

List tournaments with optional filtering.

**Query Parameters:**
- `status` (optional): Filter by status (`pending`, `registration`, `active`, `completed`)
- `netuid` (optional): Filter by network UID
- `limit` (default: 50, max: 100): Pagination limit
- `offset` (default: 0): Pagination offset

**Response Schema:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Season 4 Mainnet Tournament",
    "netuid": 2,
    "status": "active",
    "registration_start": "2024-01-01T00:00:00Z",
    "registration_end": "2024-01-10T00:00:00Z",
    "start_block": 1200,
    "end_block": 5520,
    "epoch_blocks": 360,
    "test_networks": ["mainnet", "testnet"],
    "baseline_repository": "https://github.com/subnet/baseline",
    "baseline_version": "v2.1.0",
    "created_at": "2024-01-01T00:00:00Z",
    "completed_at": null,
    "submission_count": 23
  }
]
```

**Dashboard Usage:** Tournament list page, active tournaments widget on home page.

---

### GET /api/v1/tournaments/{tournament_id}

Get detailed tournament information including all submissions and results.

**Response Schema:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Season 4 Mainnet Tournament",
  "netuid": 2,
  "status": "active",
  "registration_start": "2024-01-01T00:00:00Z",
  "registration_end": "2024-01-10T00:00:00Z",
  "start_block": 1200,
  "end_block": 5520,
  "epoch_blocks": 360,
  "test_networks": ["mainnet", "testnet"],
  "baseline_repository": "https://github.com/subnet/baseline",
  "baseline_version": "v2.1.0",
  "created_at": "2024-01-01T00:00:00Z",
  "completed_at": null,
  "submissions": [...],
  "results": [...]
}
```

**Dashboard Usage:** Tournament detail page with all data in one call.

---

### GET /api/v1/tournaments/{tournament_id}/results

Get sorted leaderboard for a tournament.

**Response Schema:**
```json
[
  {
    "id": "result-uuid",
    "tournament_id": "tournament-uuid",
    "hotkey": "5FA3b...x8Kw",
    "uid": 42,
    "pattern_accuracy_score": 0.95,
    "data_correctness_score": 0.98,
    "performance_score": 0.92,
    "final_score": 0.94,
    "rank": 1,
    "beat_baseline": true,
    "is_winner": true,
    "calculated_at": "2024-01-15T12:00:00Z"
  }
]
```

**Dashboard Usage:** Leaderboard table, winner showcase.

---

### GET /api/v1/tournaments/{tournament_id}/runs

Get evaluation runs for a tournament with filtering.

**Query Parameters:**
- `epoch_number` (optional): Filter by specific epoch
- `network` (optional): Filter by network (e.g., "mainnet", "testnet")
- `status` (optional): Filter by run status (`pending`, `running`, `completed`, `failed`)
- `limit` (default: 100, max: 500): Pagination limit
- `offset` (default: 0): Pagination offset

**Response Schema:**
```json
[
  {
    "id": "run-uuid",
    "submission_id": "submission-uuid",
    "hotkey": "5FA3b...x8Kw",
    "epoch_number": 8,
    "network": "mainnet",
    "test_date": "2024-01-12",
    "status": "completed",
    "execution_time_seconds": 45.2,
    "exit_code": 0,
    "pattern_recall": 0.94,
    "data_correctness": true,
    "started_at": "2024-01-12T10:00:00Z",
    "completed_at": "2024-01-12T10:00:45Z",
    "error_message": null
  }
]
```

**Dashboard Usage:** Evaluation timeline, epoch progress view, run details.

---

### GET /api/v1/miners/{hotkey}/history

Get complete tournament history for a specific miner.

**Response Schema:**
```json
{
  "hotkey": "5FA3b...x8Kw",
  "total_tournaments": 7,
  "total_wins": 4,
  "total_baseline_beats": 6,
  "average_rank": 2.3,
  "best_rank": 1,
  "tournaments": [
    {
      "tournament_id": "tournament-uuid",
      "tournament_name": "Season 4 Mainnet",
      "status": "active",
      "rank": 1,
      "final_score": 0.94,
      "beat_baseline": true,
      "is_winner": false,
      "submitted_at": "2024-01-05T10:00:00Z"
    }
  ]
}
```

**Dashboard Usage:** Miner profile page, performance trends chart.

---

## Dashboard UI Mockups

### Page 1: Dashboard Home

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🏆 Subnet Tournament Dashboard                           [Search Miner]   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ 🟢 ACTIVE    │  │ 👥 MINERS   │  │ 📊 RUNS     │  │ ✅ BEAT RATE │    │
│  │     3        │  │    127       │  │   2,451     │  │    67.3%     │    │
│  │ tournaments  │  │  registered  │  │  completed  │  │  vs baseline │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                                             │
│  API: GET /api/v1/stats                                                     │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  🏃 Active Tournaments                                        [View All]│
│  ├───────────────────────────────────────────────────────────────────────┤ │
│  │  Tournament Name         │ Status      │ Submissions │ Progress      │ │
│  │  Season 4 Mainnet        │ 🟢 Active   │     23      │ ████████░░ 80%│ │
│  │  Season 4 Testnet        │ 🔵 Reg Open │     15      │ ░░░░░░░░░░  0%│ │
│  │  Flash Tournament #12    │ 🟢 Active   │      8      │ ██████░░░░ 60%│ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  API: GET /api/v1/tournaments?status=active&status=registration            │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  🏆 Recent Winners (Completed Tournaments)                            │ │
│  ├───────────────────────────────────────────────────────────────────────┤ │
│  │  Season 3 Final │ Winner: 5FA3b...x8Kw │ Score: 0.94 │ Beat Baseline │ │
│  │  Flash #11      │ Winner: 7Hx2m...p5Qr │ Score: 0.89 │ Beat Baseline │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  API: GET /api/v1/tournaments?status=completed (then fetch results)        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Page 2: Tournament Detail

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ← Back │ Season 4 Mainnet Tournament                      🟢 Active       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────┐  ┌─────────────────────────────────┐ │
│  │ 📋 Tournament Info              │  │ ⏱️ Timeline                     │ │
│  │ Networks: mainnet, testnet      │  │ Registration: Dec 1 - Dec 10    │ │
│  │ Epochs: 12 (360 blocks each)    │  │ Evaluation: Block 1200 - 5520   │ │
│  │ Baseline: v2.1.0                │  │ Current Epoch: 8/12             │ │
│  └─────────────────────────────────┘  └─────────────────────────────────┘ │
│                                                                             │
│  API: GET /api/v1/tournaments/{id}                                          │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  🏆 Leaderboard                                              [Epoch ▼]│ │
│  ├───────────────────────────────────────────────────────────────────────┤ │
│  │  # │ Miner (click)   │ Pattern │ Correctness │ Perf  │ Final │ Base  │ │
│  │  1 │ 5FA3b...x8Kw    │  0.95   │    0.98     │ 0.92  │ 0.94  │  ✅   │ │
│  │  2 │ 7Hx2m...p5Qr    │  0.91   │    0.96     │ 0.88  │ 0.91  │  ✅   │ │
│  │  3 │ 3Kp7n...m2Yw    │  0.87   │    0.94     │ 0.85  │ 0.88  │  ✅   │ │
│  │  4 │ 9Tz4x...v1Lq    │  0.82   │    0.90     │ 0.79  │ 0.83  │  ❌   │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  API: GET /api/v1/tournaments/{id}/results                                  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ [Tab: Submissions] [Tab: Evaluation Runs] [Tab: Score Breakdown]       ││
│  ├─────────────────────────────────────────────────────────────────────────┤│
│  │                                                                         ││
│  │  Submissions Tab: GET /api/v1/tournaments/{id}/submissions              ││
│  │  Runs Tab: GET /api/v1/tournaments/{id}/runs?epoch_number=8             ││
│  │                                                                         ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

### Page 3: Miner Profile

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ← Back │ Miner: 5FA3b...x8Kw                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ 🏆 WINS      │  │ 📊 AVG RANK │  │ 🥇 BEST     │  │ ✅ BASELINE  │    │
│  │     4        │  │    2.3       │  │     #1      │  │    87%       │    │
│  │ tournaments  │  │  position    │  │   ranking   │  │  beat rate   │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                                             │
│  API: GET /api/v1/miners/{hotkey}/history (aggregate stats)                 │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  📜 Tournament History                                                │ │
│  ├───────────────────────────────────────────────────────────────────────┤ │
│  │  Tournament (link)  │ Status    │ Rank │ Score │ Baseline │ Winner?  │ │
│  │  Season 4 Mainnet   │ Active    │  #1  │ 0.94  │   ✅     │    -     │ │
│  │  Season 3 Final     │ Completed │  #1  │ 0.92  │   ✅     │   🏆     │ │
│  │  Flash #11          │ Completed │  #2  │ 0.89  │   ✅     │    -     │ │
│  │  Season 2 Final     │ Completed │  #1  │ 0.88  │   ✅     │   🏆     │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  API: GET /api/v1/miners/{hotkey}/history (tournaments array)               │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  📈 Performance Trend (Score over time)                               │ │
│  │  0.95 ┤                                    ●                           │ │
│  │  0.90 ┤              ●─────────●──────────╱                            │ │
│  │  0.85 ┤     ●───────╱                                                  │ │
│  │  0.80 ┤────╱                                                           │ │
│  │       └───────────────────────────────────────────────────────────────│ │
│  │        S1      S2       S3      Flash#11    S4                         │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  Chart data derived from tournaments array in history response              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## API-to-UI Mapping

| Dashboard Component | Primary API Endpoint | Data Used |
|---------------------|---------------------|-----------|
| KPI Cards (Home) | `GET /api/v1/stats` | All fields |
| Active Tournaments List | `GET /api/v1/tournaments?status=active` | name, status, submission_count |
| Tournament Info Card | `GET /api/v1/tournaments/{id}` | All tournament fields |
| Leaderboard Table | `GET /api/v1/tournaments/{id}/results` | All result fields |
| Submissions Tab | `GET /api/v1/tournaments/{id}/submissions` | All submission fields |
| Evaluation Runs Tab | `GET /api/v1/tournaments/{id}/runs` | All run fields |
| Miner Stats Cards | `GET /api/v1/miners/{hotkey}/history` | Aggregate stats |
| Miner History Table | `GET /api/v1/miners/{hotkey}/history` | tournaments array |
| Performance Chart | `GET /api/v1/miners/{hotkey}/history` | tournaments array (time series) |

---

## OpenAPI Documentation

The API provides interactive documentation at:
- **Swagger UI**: `/docs`
- **ReDoc**: `/redoc`
- **OpenAPI JSON**: `/openapi.json`

---

## Technology Stack Recommendations for Dashboard

### Frontend Framework Options
1. **React + TypeScript** - Most popular, large ecosystem
2. **Next.js** - React with SSR, great for SEO if needed
3. **Vue 3 + TypeScript** - Alternative with excellent DX

### Recommended Libraries
- **UI Framework**: Tailwind CSS + shadcn/ui or Chakra UI
- **Charts**: Recharts or Chart.js
- **Data Fetching**: TanStack Query (React Query)
- **Tables**: TanStack Table
- **State Management**: Zustand (if needed)

### Data Refresh Strategy
- Stats: Poll every 60 seconds
- Active tournaments: Poll every 30 seconds
- Results/Leaderboard: Poll every 15 seconds during active tournaments
- Use WebSockets for real-time updates (future enhancement)
