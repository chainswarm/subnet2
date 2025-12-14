from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Date,
    ForeignKey, Text, ARRAY
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
