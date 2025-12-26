"""
Database models for Analytics Tournament evaluation system.

All tables use the `analytics_tournament_` prefix to support future
multi-tournament types (ML, LLM).
"""
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Date,
    ForeignKey, Text, ARRAY, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()


# =============================================================================
# ANALYTICS TOURNAMENT TABLES
# =============================================================================

class AnalyticsTournament(Base):
    """
    Main tournament tracking table for Analytics tournaments.
    
    Analytics tournaments evaluate miners on pattern detection and feature
    generation using synthetic blockchain data.
    """
    __tablename__ = "analytics_tournaments"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    epoch_number = Column(Integer, nullable=False, unique=True)
    status = Column(String(50), nullable=False, server_default="pending")
    # Status values: pending, collecting, testing, evaluating, completed, failed
    
    # Timing
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    weights_set_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metrics
    total_submissions = Column(Integer, nullable=False, server_default="0")
    total_evaluation_runs = Column(Integer, nullable=False, server_default="0")
    
    # Configuration
    config = Column(JSONB, nullable=True)
    
    # Test networks for this tournament
    test_networks = Column(ARRAY(String), nullable=False, server_default="{}")
    
    # Baseline for comparison
    baseline_repository = Column(String(500), nullable=True)
    baseline_version = Column(String(50), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    submissions = relationship("AnalyticsTournamentSubmission", back_populates="tournament")
    results = relationship("AnalyticsTournamentResult", back_populates="tournament")
    
    def get_network_for_epoch(self, epoch_number: int) -> str:
        """
        Get network for specific epoch.
        If epoch > network count, use last network.
        
        Examples:
            networks = ["bitcoin", "zcash", "bittensor"]
            epoch 0 → bitcoin
            epoch 1 → zcash
            epoch 2 → bittensor
            epoch 3 → bittensor (repeat last)
            epoch 4 → bittensor (repeat last)
        """
        networks = self.test_networks
        if not networks:
            raise ValueError("No test networks configured")
        if epoch_number < len(networks):
            return networks[epoch_number]
        return networks[-1]
    
    @property
    def total_expected_runs(self) -> int:
        """Calculate total expected evaluation runs"""
        epoch_count = self.get_epoch_count()
        submission_count = self.total_submissions
        return epoch_count * submission_count
    
    def get_epoch_count(self) -> int:
        """Get epoch count with backward compatibility"""
        if not self.config:
            return 5  # Default
        # New format
        if "epoch_count" in self.config:
            return self.config["epoch_count"]
        # Old format fallback
        if "evaluation_days" in self.config:
            return self.config["evaluation_days"]
        # Default
        return 5


class AnalyticsTournamentSubmission(Base):
    """
    Miner submissions for analytics tournaments.
    
    Each miner can submit one Docker image per tournament.
    """
    __tablename__ = "analytics_tournament_submissions"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    tournament_id = Column(PG_UUID(as_uuid=True), ForeignKey("analytics_tournaments.id"), nullable=False)
    hotkey = Column(String(64), nullable=False)
    uid = Column(Integer, nullable=False)
    
    # Docker image reference
    docker_image_digest = Column(String(128), nullable=False)
    repository_url = Column(String(500), nullable=True)
    
    # Submission status
    status = Column(String(50), nullable=False, server_default="pending")
    # Status values: pending, validating, valid, invalid
    validation_error = Column(Text, nullable=True)
    
    submitted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    validated_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    tournament = relationship("AnalyticsTournament", back_populates="submissions")
    runs = relationship("AnalyticsTournamentEvaluationRun", back_populates="submission")
    
    __table_args__ = (
        UniqueConstraint('tournament_id', 'hotkey', name='uq_analytics_submission_tournament_hotkey'),
    )


class AnalyticsTournamentEvaluationRun(Base):
    """
    Individual evaluation runs for analytics tournaments.
    
    Each submission is evaluated multiple times across different test dates
    and networks. This table stores the detailed results of each run.
    """
    __tablename__ = "analytics_tournament_evaluation_runs"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    submission_id = Column(PG_UUID(as_uuid=True), ForeignKey("analytics_tournament_submissions.id"), nullable=False)
    
    # Run context
    epoch_number = Column(Integer, nullable=False)
    network = Column(String(50), nullable=False)
    test_date = Column(Date, nullable=False)
    
    status = Column(String(50), nullable=False, server_default="pending")
    # Status values: pending, running, completed, failed, timeout
    
    # ==========================================================================
    # Gate 1: Output Schema Validation
    # ==========================================================================
    output_schema_valid = Column(Boolean, nullable=True)
    feature_generation_time_seconds = Column(Float, nullable=True)
    
    # ==========================================================================
    # Gate 2: Pattern Validation (via flow tracing)
    # ==========================================================================
    pattern_existence = Column(Boolean, nullable=True)
    patterns_reported = Column(Integer, nullable=True)  # Total patterns miner claimed
    
    # Synthetic Patterns (from ground_truth)
    synthetic_addresses_expected = Column(Integer, nullable=True)  # Addresses in ground_truth
    synthetic_addresses_found = Column(Integer, nullable=True)     # Correctly detected
    
    # Novelty Patterns (miner discoveries)
    novelty_patterns_valid = Column(Integer, nullable=True)    # Verified via flow tracing
    novelty_patterns_invalid = Column(Integer, nullable=True)  # Fake - flows don't exist
    
    pattern_detection_time_seconds = Column(Float, nullable=True)
    
    # ==========================================================================
    # Computed Scores (0.0 to 1.0)
    # ==========================================================================
    feature_performance_score = Column(Float, nullable=True)   # 10% weight
    synthetic_recall_score = Column(Float, nullable=True)      # 30% weight
    pattern_precision_score = Column(Float, nullable=True)     # 25% weight (anti-cheat)
    novelty_discovery_score = Column(Float, nullable=True)     # 25% weight
    pattern_performance_score = Column(Float, nullable=True)   # 10% weight
    
    # Final Score
    final_score = Column(Float, nullable=True)
    
    # ==========================================================================
    # Execution Metadata
    # ==========================================================================
    exit_code = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    submission = relationship("AnalyticsTournamentSubmission", back_populates="runs")


class AnalyticsTournamentResult(Base):
    """
    Aggregated results per miner per tournament.
    
    Summarizes all evaluation runs into final tournament standings.
    """
    __tablename__ = "analytics_tournament_results"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    tournament_id = Column(PG_UUID(as_uuid=True), ForeignKey("analytics_tournaments.id"), nullable=False)
    hotkey = Column(String(64), nullable=False)
    uid = Column(Integer, nullable=False)
    
    # ==========================================================================
    # Aggregated Scores (means across all runs)
    # ==========================================================================
    
    # Gate pass rates
    output_schema_validity_rate = Column(Float, nullable=True)  # % of runs with valid output
    pattern_existence_rate = Column(Float, nullable=True)       # % of runs with valid patterns
    
    # Component scores (0.0 to 1.0)
    feature_performance_score = Column(Float, nullable=True)    # Mean feature performance (10%)
    synthetic_recall_score = Column(Float, nullable=True)       # Mean synthetic recall (30%)
    pattern_precision_score = Column(Float, nullable=True)      # Mean precision (25%)
    novelty_discovery_score = Column(Float, nullable=True)      # Mean novelty score (25%)
    pattern_performance_score = Column(Float, nullable=True)    # Mean pattern performance (10%)
    
    # ==========================================================================
    # Totals across all runs
    # ==========================================================================
    total_runs = Column(Integer, nullable=True)
    total_patterns_reported = Column(Integer, nullable=True)
    total_synthetic_found = Column(Integer, nullable=True)
    total_novelty_valid = Column(Integer, nullable=True)
    total_novelty_invalid = Column(Integer, nullable=True)
    
    # Final aggregated score
    final_score = Column(Float, nullable=False)
    
    # Ranking
    rank = Column(Integer, nullable=False)
    beat_baseline = Column(Boolean, nullable=False, server_default="false")
    is_winner = Column(Boolean, nullable=False, server_default="false")
    
    calculated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    tournament = relationship("AnalyticsTournament", back_populates="results")
    
    __table_args__ = (
        UniqueConstraint('tournament_id', 'hotkey', name='uq_analytics_result_tournament_hotkey'),
    )


# =============================================================================
# LEGACY TABLES (for backward compatibility during migration)
# =============================================================================

class Tournament(Base):
    """
    DEPRECATED: Use AnalyticsTournament instead.
    Kept for backward compatibility during migration.
    """
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
    """
    DEPRECATED: Use AnalyticsTournamentSubmission instead.
    """
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
    """
    DEPRECATED: Use AnalyticsTournamentEvaluationRun instead.
    """
    __tablename__ = "evaluation_runs"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    submission_id = Column(PG_UUID(as_uuid=True), ForeignKey("submissions.id"), nullable=False)
    
    epoch_number = Column(Integer, nullable=False)
    network = Column(String(50), nullable=False)
    test_date = Column(Date, nullable=False)
    
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
    """
    DEPRECATED: Use AnalyticsTournamentResult instead.
    """
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
