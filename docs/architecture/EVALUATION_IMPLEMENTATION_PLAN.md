# Evaluation Framework Implementation Plan

**Date**: 2025-12-14  
**Status**: Work Breakdown for Coding Agent  
**Prerequisite**: [`EVALUATION_FRAMEWORK_ARCHITECTURE.md`](EVALUATION_FRAMEWORK_ARCHITECTURE.md)

---

## ☢️ Reactor Protocol Compliance

This implementation follows the [Reactor Protocol](../../../reactor-core/.roo/rules/001-reactor-protocol.md).

### Critical Rules for Coding Agent

| Rule | Implication |
|------|-------------|
| ❌ No tests | User validates by running |
| ❌ No fallbacks | `raise ValueError()` not `return None` |
| ❌ No docstrings | Method names are self-descriptive |
| ❌ No comments | Code is self-documenting |
| ❌ No migrations of existing data | We start fresh, always |
| ✅ Fail fast | Exceptions over silent failures |
| ✅ Loguru | `from loguru import logger` |
| ✅ Type hints | All functions typed |
| ✅ Bash only | No PowerShell |

---

## Work Breakdown

### Task 1: Project Structure Setup

**Create the evaluation module structure in subnet2:**

```
subnet2/
├── alembic/                    # NEW: Alembic migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 001_tournaments.py
├── alembic.ini                 # NEW: Alembic config
├── evaluation/                 # NEW: Evaluation module
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── database.py        # SQLAlchemy Base & models
│   │   ├── tournament.py      # Pydantic models
│   │   └── results.py         # Result dataclasses
│   ├── managers/
│   │   ├── __init__.py
│   │   ├── tournament_manager.py
│   │   ├── submission_manager.py
│   │   ├── docker_manager.py
│   │   └── scoring_manager.py
│   ├── security/
│   │   ├── __init__.py
│   │   ├── code_scanner.py
│   │   └── seccomp.json
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── epoch_start_task.py
│   │   ├── evaluation_task.py
│   │   └── epoch_end_task.py
│   └── repositories/
│       ├── __init__.py
│       └── tournament_repository.py
├── config.py                   # NEW: Settings with DB URL
└── template/
    └── protocol.py             # UPDATE: Add SubmissionSynapse
```

**Files to create:**
- `alembic.ini`
- `alembic/env.py`
- `alembic/script.py.mako`
- `evaluation/__init__.py`
- `config.py`

---

### Task 2: Config Module

**File: `subnet2/config.py`**

Pattern: Same as [`gateway/package/config.py`](../../../gateway/package/config.py)

```python
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "subnet2"
    postgres_user: str = "subnet2"
    postgres_password: str
    
    redis_url: str = "redis://localhost:6379/0"
    
    repos_path: str = "/tmp/evaluation/repos"
    data_path: str = "/tmp/evaluation/data"
    
    benchmark_max_execution_time: int = 3600
    benchmark_memory_limit: str = "32g"
    
    class Config:
        env_prefix = ""

    def get_database_url(self) -> str:
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"


config = Settings()
```

---

### Task 3: SQLAlchemy Models

**File: `subnet2/evaluation/models/database.py`**

Pattern: Same as [`gateway/package/models/database.py`](../../../gateway/package/models/database.py)

```python
from datetime import datetime
from uuid import UUID
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, 
    ForeignKey, Text, create_engine, ARRAY
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()


class Tournament(Base):
    __tablename__ = "tournaments"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    name = Column(String(255), nullable=False)
    netuid = Column(Integer, nullable=False)
    status = Column(String(50), nullable=False, server_default="pending")
    
    registration_start = Column(DateTime(timezone=True), nullable=False)
    registration_end = Column(DateTime(timezone=True), nullable=False)
    start_block = Column(Integer, nullable=False)
    end_block = Column(Integer, nullable=False)
    
    epoch_blocks = Column(Integer, nullable=False, server_default="360")
    test_networks = Column(ARRAY(String), nullable=False)
    
    baseline_repository = Column(String(500), nullable=True)
    baseline_version = Column(String(50), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    submissions = relationship("Submission", back_populates="tournament")
    results = relationship("TournamentResult", back_populates="tournament")


class Submission(Base):
    __tablename__ = "submissions"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    tournament_id = Column(PG_UUID(as_uuid=True), ForeignKey("tournaments.id"), nullable=False)
    hotkey = Column(String(64), nullable=False)
    uid = Column(Integer, nullable=False)
    
    repository_url = Column(String(500), nullable=False)
    commit_hash = Column(String(40), nullable=False)
    docker_image_tag = Column(String(255), nullable=True)
    
    status = Column(String(50), nullable=False, server_default="pending")
    validation_error = Column(Text, nullable=True)
    
    submitted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    validated_at = Column(DateTime(timezone=True), nullable=True)
    
    tournament = relationship("Tournament", back_populates="submissions")
    runs = relationship("EvaluationRun", back_populates="submission")


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    submission_id = Column(PG_UUID(as_uuid=True), ForeignKey("submissions.id"), nullable=False)
    
    epoch_number = Column(Integer, nullable=False)
    network = Column(String(50), nullable=False)
    test_date = Column(DateTime, nullable=False)
    
    status = Column(String(50), nullable=False, server_default="pending")
    execution_time_seconds = Column(Float, nullable=True)
    exit_code = Column(Integer, nullable=True)
    
    pattern_recall = Column(Float, nullable=True)
    data_correctness = Column(Boolean, nullable=True)
    
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    
    submission = relationship("Submission", back_populates="runs")


class TournamentResult(Base):
    __tablename__ = "tournament_results"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    tournament_id = Column(PG_UUID(as_uuid=True), ForeignKey("tournaments.id"), nullable=False)
    hotkey = Column(String(64), nullable=False)
    uid = Column(Integer, nullable=False)
    
    pattern_accuracy_score = Column(Float, nullable=False)
    data_correctness_score = Column(Float, nullable=False)
    performance_score = Column(Float, nullable=False)
    final_score = Column(Float, nullable=False)
    
    rank = Column(Integer, nullable=False)
    beat_baseline = Column(Boolean, nullable=False, server_default="false")
    is_winner = Column(Boolean, nullable=False, server_default="false")
    
    calculated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    tournament = relationship("Tournament", back_populates="results")
```

---

### Task 4: Alembic Setup

**File: `subnet2/alembic.ini`**

```ini
[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator = os

sqlalchemy.url = driver://user:pass@localhost/dbname

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

**File: `subnet2/alembic/env.py`**

```python
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

from config import config as app_config
from evaluation.models.database import Base

config = context.config

config.set_main_option("sqlalchemy.url", app_config.get_database_url())

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

**File: `subnet2/alembic/versions/001_tournaments.py`**

```python
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'tournaments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('netuid', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('registration_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('registration_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('start_block', sa.Integer(), nullable=False),
        sa.Column('end_block', sa.Integer(), nullable=False),
        sa.Column('epoch_blocks', sa.Integer(), nullable=False, server_default='360'),
        sa.Column('test_networks', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('baseline_repository', sa.String(500), nullable=True),
        sa.Column('baseline_version', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_tournaments_netuid', 'tournaments', ['netuid'])
    op.create_index('idx_tournaments_status', 'tournaments', ['status'])
    
    op.create_table(
        'submissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tournament_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('hotkey', sa.String(64), nullable=False),
        sa.Column('uid', sa.Integer(), nullable=False),
        sa.Column('repository_url', sa.String(500), nullable=False),
        sa.Column('commit_hash', sa.String(40), nullable=False),
        sa.Column('docker_image_tag', sa.String(255), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('validation_error', sa.Text(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('validated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tournament_id'], ['tournaments.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tournament_id', 'hotkey', name='unique_tournament_hotkey')
    )
    op.create_index('idx_submissions_tournament', 'submissions', ['tournament_id'])
    op.create_index('idx_submissions_hotkey', 'submissions', ['hotkey'])
    
    op.create_table(
        'evaluation_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('submission_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('epoch_number', sa.Integer(), nullable=False),
        sa.Column('network', sa.String(50), nullable=False),
        sa.Column('test_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('execution_time_seconds', sa.Float(), nullable=True),
        sa.Column('exit_code', sa.Integer(), nullable=True),
        sa.Column('pattern_recall', sa.Float(), nullable=True),
        sa.Column('data_correctness', sa.Boolean(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['submission_id'], ['submissions.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_evaluation_runs_submission', 'evaluation_runs', ['submission_id'])
    
    op.create_table(
        'tournament_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tournament_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('hotkey', sa.String(64), nullable=False),
        sa.Column('uid', sa.Integer(), nullable=False),
        sa.Column('pattern_accuracy_score', sa.Float(), nullable=False),
        sa.Column('data_correctness_score', sa.Float(), nullable=False),
        sa.Column('performance_score', sa.Float(), nullable=False),
        sa.Column('final_score', sa.Float(), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('beat_baseline', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_winner', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('calculated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['tournament_id'], ['tournaments.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tournament_id', 'hotkey', name='unique_result_tournament_hotkey')
    )
    op.create_index('idx_tournament_results_score', 'tournament_results', ['tournament_id', 'final_score'])


def downgrade() -> None:
    op.drop_table('tournament_results')
    op.drop_table('evaluation_runs')
    op.drop_table('submissions')
    op.drop_table('tournaments')
```

---

### Task 5: Tournament Repository

**File: `subnet2/evaluation/repositories/tournament_repository.py`**

```python
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from evaluation.models.database import Tournament, Submission, EvaluationRun, TournamentResult


class TournamentRepository:
    def __init__(self, session: Session):
        self.session = session
    
    def create_tournament(self, tournament: Tournament) -> Tournament:
        self.session.add(tournament)
        self.session.commit()
        self.session.refresh(tournament)
        return tournament
    
    def get_by_id(self, tournament_id: UUID) -> Tournament:
        tournament = self.session.query(Tournament).filter(Tournament.id == tournament_id).first()
        if not tournament:
            raise ValueError(f"tournament_not_found: {tournament_id}")
        return tournament
    
    def get_active_by_netuid(self, netuid: int) -> Optional[Tournament]:
        return self.session.query(Tournament).filter(
            Tournament.netuid == netuid,
            Tournament.status.in_(["registration", "active"])
        ).first()
    
    def update_status(self, tournament_id: UUID, status: str) -> Tournament:
        tournament = self.get_by_id(tournament_id)
        tournament.status = status
        if status == "completed":
            tournament.completed_at = datetime.utcnow()
        self.session.commit()
        return tournament
    
    def create_submission(self, submission: Submission) -> Submission:
        self.session.add(submission)
        self.session.commit()
        self.session.refresh(submission)
        return submission
    
    def get_submissions_by_tournament(self, tournament_id: UUID) -> List[Submission]:
        return self.session.query(Submission).filter(
            Submission.tournament_id == tournament_id
        ).all()
    
    def get_submission_by_hotkey(self, tournament_id: UUID, hotkey: str) -> Optional[Submission]:
        return self.session.query(Submission).filter(
            Submission.tournament_id == tournament_id,
            Submission.hotkey == hotkey
        ).first()
    
    def update_submission_status(self, submission_id: UUID, status: str, error: Optional[str] = None) -> Submission:
        submission = self.session.query(Submission).filter(Submission.id == submission_id).first()
        if not submission:
            raise ValueError(f"submission_not_found: {submission_id}")
        submission.status = status
        if error:
            submission.validation_error = error
        if status == "validated":
            submission.validated_at = datetime.utcnow()
        self.session.commit()
        return submission
    
    def create_evaluation_run(self, run: EvaluationRun) -> EvaluationRun:
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)
        return run
    
    def get_runs_by_submission(self, submission_id: UUID) -> List[EvaluationRun]:
        return self.session.query(EvaluationRun).filter(
            EvaluationRun.submission_id == submission_id
        ).all()
    
    def create_result(self, result: TournamentResult) -> TournamentResult:
        self.session.add(result)
        self.session.commit()
        self.session.refresh(result)
        return result
    
    def get_results_by_tournament(self, tournament_id: UUID) -> List[TournamentResult]:
        return self.session.query(TournamentResult).filter(
            TournamentResult.tournament_id == tournament_id
        ).order_by(TournamentResult.rank).all()
```

---

### Task 6: Submission Synapse Protocol

**File: `subnet2/template/protocol.py`** (UPDATE existing file)

Add after the existing `Dummy` synapse:

```python
class SubmissionSynapse(bt.Synapse):
    tournament_id: str
    epoch_number: int
    
    repository_url: typing.Optional[str] = None
    commit_hash: typing.Optional[str] = None
    
    def deserialize(self) -> dict:
        return {
            "repository_url": self.repository_url,
            "commit_hash": self.commit_hash,
        }
```

---

### Task 7: Managers (Port from data-pipeline)

**Source files to port:**

| Source | Destination | Changes |
|--------|-------------|---------|
| `data-pipeline/packages/evaluation/managers/repository_manager.py` | `subnet2/evaluation/managers/submission_manager.py` | Rename class, use loguru, remove docstrings |
| `data-pipeline/packages/evaluation/managers/docker_manager.py` | `subnet2/evaluation/managers/docker_manager.py` | Use local config, parquet I/O only |
| `data-pipeline/packages/evaluation/managers/scoring_manager.py` | `subnet2/evaluation/managers/scoring_manager.py` | Remove ClickHouse, read parquet |
| `data-pipeline/packages/evaluation/managers/validation_manager.py` | `subnet2/evaluation/managers/scoring_manager.py` | Merge into scoring, parquet only |

**Key transformations:**

1. Remove all docstrings
2. Replace `os.environ["KEY"]` with `config.key`
3. Replace ClickHouse reads with parquet reads
4. Use `raise ValueError()` instead of returning None
5. Use `from loguru import logger`

---

### Task 8: Celery Tasks

**File: `subnet2/evaluation/tasks/__init__.py`**

```python
from chainswarm_core.jobs import create_celery_app

celery_app = create_celery_app(
    name="evaluation",
    autodiscover=["evaluation.tasks"],
    beat_schedule_path="evaluation/beat_schedule.json",
)
```

**File: `subnet2/evaluation/beat_schedule.json`**

```json
{
    "epoch-start": {
        "task": "evaluation.tasks.epoch_start_task.start_epoch",
        "schedule": "0 0 * * *",
        "args": []
    },
    "daily-evaluation": {
        "task": "evaluation.tasks.evaluation_task.run_evaluations",
        "schedule": "0 */4 * * *",
        "args": []
    },
    "epoch-end": {
        "task": "evaluation.tasks.epoch_end_task.end_epoch",
        "schedule": "0 23 * * *",
        "args": []
    }
}
```

---

### Task 9: Security Module (Port from data-pipeline)

**Files to port:**

| Source | Destination |
|--------|-------------|
| `data-pipeline/packages/evaluation/security/code_scanner.py` | `subnet2/evaluation/security/code_scanner.py` |
| `data-pipeline/packages/evaluation/security/seccomp-miner.json` | `subnet2/evaluation/security/seccomp.json` |

**Changes:**
- Remove docstrings
- Use loguru
- Use config instead of os.environ

---

### Task 10: Update requirements.txt

Add to `subnet2/requirements.txt`:

```
# Database
sqlalchemy>=2.0.0
alembic>=1.13.0
psycopg2-binary>=2.9.9

# Task Queue
celery>=5.3.0
redis>=5.0.0

# Docker
docker>=7.0.0

# Data
pandas>=2.0.0
pyarrow>=14.0.0

# Logging
loguru>=0.7.0

# Core
chainswarm-core
```

---

## Implementation Order

```mermaid
gantt
    title Implementation Timeline
    dateFormat  YYYY-MM-DD
    section Foundation
    Task 1 - Structure Setup    :t1, 2025-01-01, 1d
    Task 2 - Config Module      :t2, after t1, 1d
    Task 3 - SQLAlchemy Models  :t3, after t2, 1d
    Task 4 - Alembic Setup      :t4, after t3, 1d
    section Data Layer
    Task 5 - Repository         :t5, after t4, 1d
    section Protocol
    Task 6 - Synapse            :t6, after t4, 1d
    section Business Logic
    Task 7 - Managers           :t7, after t5, 2d
    Task 8 - Celery Tasks       :t8, after t7, 2d
    Task 9 - Security           :t9, after t6, 1d
    section Integration
    Task 10 - Requirements      :t10, after t9, 1d
```

---

## Validation Checklist

After each task, verify:

- [ ] No docstrings created
- [ ] No comments explaining "why"
- [ ] All functions have type hints
- [ ] Exceptions raised for errors (not `return None`)
- [ ] Uses `from loguru import logger`
- [ ] No emoticons in log messages
- [ ] Uses config settings (not `os.environ`)
- [ ] Bash only for any scripts

---

## Test by Running

The user validates by running:

```bash
# 1. Start PostgreSQL & Redis
cd subnet2
docker-compose up -d postgres redis

# 2. Run migrations
alembic upgrade head

# 3. Start validator
python scripts/run_validator.py --netuid 1

# 4. Check logs for errors
```

No test files. No mocks. Real systems only.
