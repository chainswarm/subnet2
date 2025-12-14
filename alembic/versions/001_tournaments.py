"""tournaments

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


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
