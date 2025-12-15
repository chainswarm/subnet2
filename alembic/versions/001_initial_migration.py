"""Initial migration with all tables

Revision ID: 001_initial_migration
Revises: 
Create Date: 2025-12-15 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_migration'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==========================================================================
    # ANALYTICS TOURNAMENT TABLES
    # ==========================================================================
    
    # analytics_tournaments - Main tournament tracking table
    op.create_table(
        'analytics_tournaments',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('epoch_number', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(50), server_default='pending', nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_submissions', sa.Integer(), server_default='0', nullable=False),
        sa.Column('total_evaluation_runs', sa.Integer(), server_default='0', nullable=False),
        sa.Column('config', postgresql.JSONB(), nullable=True),
        sa.Column('test_networks', postgresql.ARRAY(sa.String()), server_default='{}', nullable=False),
        sa.Column('baseline_repository', sa.String(500), nullable=True),
        sa.Column('baseline_version', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('epoch_number'),
    )
    
    op.create_index(
        'ix_analytics_tournaments_status',
        'analytics_tournaments',
        ['status']
    )
    op.create_index(
        'ix_analytics_tournaments_epoch_number',
        'analytics_tournaments',
        ['epoch_number']
    )
    
    # analytics_tournament_submissions - Miner submissions
    op.create_table(
        'analytics_tournament_submissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tournament_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('hotkey', sa.String(64), nullable=False),
        sa.Column('uid', sa.Integer(), nullable=False),
        sa.Column('docker_image_digest', sa.String(128), nullable=False),
        sa.Column('repository_url', sa.String(500), nullable=True),
        sa.Column('status', sa.String(50), server_default='pending', nullable=False),
        sa.Column('validation_error', sa.Text(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('validated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tournament_id'], ['analytics_tournaments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tournament_id', 'hotkey', name='uq_analytics_submission_tournament_hotkey'),
    )
    
    op.create_index(
        'ix_analytics_tournament_submissions_hotkey',
        'analytics_tournament_submissions',
        ['hotkey']
    )
    op.create_index(
        'ix_analytics_tournament_submissions_tournament_id',
        'analytics_tournament_submissions',
        ['tournament_id']
    )
    
    # analytics_tournament_evaluation_runs - Individual evaluation runs
    op.create_table(
        'analytics_tournament_evaluation_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('submission_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Run context
        sa.Column('epoch_number', sa.Integer(), nullable=False),
        sa.Column('network', sa.String(50), nullable=False),
        sa.Column('test_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(50), server_default='pending', nullable=False),
        
        # Gate 1: Output Schema Validation
        sa.Column('output_schema_valid', sa.Boolean(), nullable=True),
        sa.Column('feature_generation_time_seconds', sa.Float(), nullable=True),
        
        # Gate 2: Pattern Validation
        sa.Column('pattern_existence', sa.Boolean(), nullable=True),
        sa.Column('patterns_reported', sa.Integer(), nullable=True),
        
        # Synthetic Patterns (from ground_truth)
        sa.Column('synthetic_addresses_expected', sa.Integer(), nullable=True),
        sa.Column('synthetic_addresses_found', sa.Integer(), nullable=True),
        
        # Novelty Patterns (miner discoveries)
        sa.Column('novelty_patterns_valid', sa.Integer(), nullable=True),
        sa.Column('novelty_patterns_invalid', sa.Integer(), nullable=True),
        
        sa.Column('pattern_detection_time_seconds', sa.Float(), nullable=True),
        
        # Computed Scores (0.0 to 1.0)
        sa.Column('feature_performance_score', sa.Float(), nullable=True),
        sa.Column('synthetic_recall_score', sa.Float(), nullable=True),
        sa.Column('pattern_precision_score', sa.Float(), nullable=True),
        sa.Column('novelty_discovery_score', sa.Float(), nullable=True),
        sa.Column('pattern_performance_score', sa.Float(), nullable=True),
        
        # Final Score
        sa.Column('final_score', sa.Float(), nullable=True),
        
        # Execution Metadata
        sa.Column('exit_code', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        
        sa.ForeignKeyConstraint(['submission_id'], ['analytics_tournament_submissions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    
    op.create_index(
        'ix_analytics_tournament_evaluation_runs_submission_id',
        'analytics_tournament_evaluation_runs',
        ['submission_id']
    )
    op.create_index(
        'ix_analytics_tournament_evaluation_runs_epoch_number',
        'analytics_tournament_evaluation_runs',
        ['epoch_number']
    )
    op.create_index(
        'ix_analytics_tournament_evaluation_runs_status',
        'analytics_tournament_evaluation_runs',
        ['status']
    )
    
    # analytics_tournament_results - Aggregated results per miner
    op.create_table(
        'analytics_tournament_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tournament_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('hotkey', sa.String(64), nullable=False),
        sa.Column('uid', sa.Integer(), nullable=False),
        
        # Gate pass rates
        sa.Column('output_schema_validity_rate', sa.Float(), nullable=True),
        sa.Column('pattern_existence_rate', sa.Float(), nullable=True),
        
        # Aggregated Scores
        sa.Column('feature_performance_score', sa.Float(), nullable=True),
        sa.Column('synthetic_recall_score', sa.Float(), nullable=True),
        sa.Column('pattern_precision_score', sa.Float(), nullable=True),
        sa.Column('novelty_discovery_score', sa.Float(), nullable=True),
        sa.Column('pattern_performance_score', sa.Float(), nullable=True),
        
        # Totals
        sa.Column('total_runs', sa.Integer(), nullable=True),
        sa.Column('total_patterns_reported', sa.Integer(), nullable=True),
        sa.Column('total_synthetic_found', sa.Integer(), nullable=True),
        sa.Column('total_novelty_valid', sa.Integer(), nullable=True),
        sa.Column('total_novelty_invalid', sa.Integer(), nullable=True),
        
        # Final Score and Ranking
        sa.Column('final_score', sa.Float(), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('beat_baseline', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('is_winner', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('calculated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        
        sa.ForeignKeyConstraint(['tournament_id'], ['analytics_tournaments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tournament_id', 'hotkey', name='uq_analytics_result_tournament_hotkey'),
    )
    
    op.create_index(
        'ix_analytics_tournament_results_tournament_id',
        'analytics_tournament_results',
        ['tournament_id']
    )
    op.create_index(
        'ix_analytics_tournament_results_hotkey',
        'analytics_tournament_results',
        ['hotkey']
    )
    op.create_index(
        'ix_analytics_tournament_results_rank',
        'analytics_tournament_results',
        ['rank']
    )
    
    # ==========================================================================
    # LEGACY TABLES (for backward compatibility)
    # ==========================================================================
    
    # tournaments (legacy)
    op.create_table(
        'tournaments',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('netuid', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(50), server_default='pending', nullable=False),
        sa.Column('registration_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('registration_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('start_block', sa.Integer(), nullable=False),
        sa.Column('end_block', sa.Integer(), nullable=False),
        sa.Column('epoch_blocks', sa.Integer(), server_default='360', nullable=False),
        sa.Column('test_networks', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('baseline_repository', sa.String(500), nullable=True),
        sa.Column('baseline_version', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('idx_tournaments_netuid', 'tournaments', ['netuid'])
    op.create_index('idx_tournaments_status', 'tournaments', ['status'])
    
    # submissions (legacy)
    op.create_table(
        'submissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tournament_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('hotkey', sa.String(64), nullable=False),
        sa.Column('uid', sa.Integer(), nullable=False),
        sa.Column('repository_url', sa.String(500), nullable=False),
        sa.Column('commit_hash', sa.String(40), nullable=False),
        sa.Column('docker_image_tag', sa.String(255), nullable=True),
        sa.Column('status', sa.String(50), server_default='pending', nullable=False),
        sa.Column('validation_error', sa.Text(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('validated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tournament_id'], ['tournaments.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tournament_id', 'hotkey', name='unique_tournament_hotkey')
    )
    
    op.create_index('idx_submissions_tournament', 'submissions', ['tournament_id'])
    op.create_index('idx_submissions_hotkey', 'submissions', ['hotkey'])
    
    # evaluation_runs (legacy)
    op.create_table(
        'evaluation_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('submission_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('epoch_number', sa.Integer(), nullable=False),
        sa.Column('network', sa.String(50), nullable=False),
        sa.Column('test_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(50), server_default='pending', nullable=False),
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
    
    # tournament_results (legacy)
    op.create_table(
        'tournament_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tournament_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('hotkey', sa.String(64), nullable=False),
        sa.Column('uid', sa.Integer(), nullable=False),
        sa.Column('pattern_accuracy_score', sa.Float(), nullable=False),
        sa.Column('data_correctness_score', sa.Float(), nullable=False),
        sa.Column('performance_score', sa.Float(), nullable=False),
        sa.Column('final_score', sa.Float(), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('beat_baseline', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('is_winner', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('calculated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tournament_id'], ['tournaments.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tournament_id', 'hotkey', name='unique_result_tournament_hotkey')
    )
    
    op.create_index('idx_tournament_results_score', 'tournament_results', ['tournament_id', 'final_score'])


def downgrade() -> None:
    # Drop legacy tables first
    op.drop_table('tournament_results')
    op.drop_table('evaluation_runs')
    op.drop_table('submissions')
    op.drop_table('tournaments')
    
    # Drop analytics tables in reverse order (due to foreign key constraints)
    op.drop_table('analytics_tournament_results')
    op.drop_table('analytics_tournament_evaluation_runs')
    op.drop_table('analytics_tournament_submissions')
    op.drop_table('analytics_tournaments')
