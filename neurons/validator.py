# The MIT License (MIT)
# Copyright © 2023 Yuma Rao
# Copyright © 2024 ChainSwarm

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import List

import bittensor as bt
import torch
import numpy as np

from template.base.validator import BaseValidatorNeuron
from template.protocol import SubmissionSynapse
from evaluation.db import get_session
from evaluation.models.database import AnalyticsTournament, AnalyticsTournamentSubmission
from evaluation.repositories.tournament_repository import TournamentRepository
from evaluation.tasks.epoch_orchestrator_task import orchestrate_tournament_task
from config import config


class Validator(BaseValidatorNeuron):
    """
    Analytics Tournament Validator - Tournament State Machine.
    
    This validator manages tournament lifecycle via a state machine:
    1. PRE_TOURNAMENT: Collect submissions from miners via dendrite
    2. IN_TOURNAMENT: Celery evaluates submissions
    3. AWAITING_WEIGHTS: Validator sets weights from DB results
    4. Cycle repeats
    
    The validator is the ONLY component that touches Bittensor (wallet, subtensor, dendrite).
    Celery workers only perform evaluation (Docker, scoring) and write to PostgreSQL.
    """

    def __init__(self, config=None):
        super(Validator, self).__init__(config=config)
        bt.logging.info("Analytics Tournament Validator initialized - state machine mode")

    def get_tournament_state(self) -> str:
        """Derive tournament state from existing DB tables (no extra state storage)."""
        session = get_session()
        repo = TournamentRepository(session)
        
        try:
            active = repo.get_active_tournament()
            
            if active is None:
                return "PRE_TOURNAMENT"  # No tournament → start collecting
            
            if active.status in ["pending", "collecting"]:
                return "PRE_TOURNAMENT"  # Submission window open
            
            if active.status in ["in_progress", "evaluating"]:
                return "IN_TOURNAMENT"  # Celery is evaluating
            
            if active.status == "completed" and active.weights_set_at is None:
                return "AWAITING_WEIGHTS"  # Need to set weights
            
            return "DONE"  # Weights set, will transition to new tournament
        finally:
            session.close()

    async def collect_submissions(self):
        """
        Query all miners for their submissions via dendrite.
        
        Upserts submissions to DB (only saves if changed).
        This runs continuously during PRE_TOURNAMENT state.
        """
        session = get_session()
        repo = TournamentRepository(session)
        
        try:
            tournament = repo.get_active_tournament()
            
            if not tournament:
                # Create new tournament
                now = datetime.now(timezone.utc)
                tournament = AnalyticsTournament(
                    id=uuid.uuid4(),
                    epoch_number=self._next_epoch_number(repo),
                    status="collecting",
                    started_at=now,
                    total_submissions=0,
                    total_evaluation_runs=0,
                    config={
                        "submission_duration_seconds": config.tournament_submission_duration_seconds,
                        "epoch_count": config.tournament_epoch_count,
                        "epoch_duration_seconds": config.tournament_epoch_duration_seconds,
                        "baseline_repository": "https://github.com/chainswarm/analyzers-baseline",
                        "baseline_version": "0.1.3",
                    },
                    test_networks=config.tournament_networks_list,
                    created_at=now,
                )
                tournament = repo.create_tournament(tournament)
                bt.logging.info(f"Created tournament {tournament.id} for epoch {tournament.epoch_number}")

            # Query all miners via dendrite
            synapse = SubmissionSynapse(
                tournament_id=str(tournament.id),
                epoch_number=tournament.epoch_number,
            )

            responses = await self.dendrite(
                axons=self.metagraph.axons,
                synapse=synapse,
                timeout=config.submission_timeout_seconds,
                deserialize=False,  # Keep synapse objects, don't deserialize
            )

            # Upsert submissions (only if changed)
            submission_count = 0
            for uid, response in enumerate(responses):
                # Validate response is a SubmissionSynapse object
                if not isinstance(response, SubmissionSynapse):
                    bt.logging.warning(f"Invalid response type from UID {uid}: {type(response)}")
                    continue
                
                # Check if response has valid data
                if not hasattr(response, 'repository_url') or not hasattr(response, 'commit_hash'):
                    bt.logging.warning(f"Response from UID {uid} missing required attributes")
                    continue
                
                repo_url = response.repository_url
                commit = response.commit_hash
                
                # Skip empty/invalid submissions
                if not repo_url or not commit:
                    bt.logging.debug(f"UID {uid} did not provide submission")
                    continue
                
                # Check if submission exists
                existing = repo.get_submission_by_tournament_and_uid(tournament.id, uid)
                
                if existing:
                    # Update only if changed
                    if (existing.repository_url != repo_url or
                        existing.commit_hash != commit):
                        existing.repository_url = repo_url
                        existing.commit_hash = commit
                        existing.submitted_at = datetime.now(timezone.utc)
                        bt.logging.info(f"Updated submission for UID {uid}")
                else:
                    # Create new submission
                    submission = AnalyticsTournamentSubmission(
                        id=uuid.uuid4(),
                        tournament_id=tournament.id,
                        hotkey=self.metagraph.hotkeys[uid],
                        uid=uid,
                        repository_url=repo_url,
                        commit_hash=commit,
                        docker_image_digest="",
                        status="pending",
                        submitted_at=datetime.now(timezone.utc),
                    )
                    repo.create_submission(submission)
                    bt.logging.info(f"New submission from UID {uid}: {repo_url}@{commit}")
                
                submission_count += 1

            # Check if submission window has closed
            elapsed = (datetime.now(timezone.utc) - tournament.started_at).total_seconds()
            if elapsed >= config.tournament_submission_duration_seconds:
                # Close submission window, trigger Celery
                repo.update_status(tournament.id, "in_progress")
                tournament.total_submissions = submission_count
                session.commit()
                
                # Kick off Celery orchestrator
                orchestrate_tournament_task.apply_async(args=[str(tournament.id)])
                bt.logging.info(f"Submission window closed for tournament {tournament.id}. "
                              f"Collected {submission_count} submissions. Triggered evaluation.")

        except Exception as e:
            bt.logging.error(f"Error collecting submissions: {e}")
        finally:
            session.close()

    def _next_epoch_number(self, repo: TournamentRepository) -> int:
        """Calculate next epoch number."""
        last = repo.get_latest_tournament()
        return (last.epoch_number + 1) if last else 1

    async def forward(self):
        """
        State machine forward pass.
        
        Determines tournament state and executes appropriate action:
        - PRE_TOURNAMENT: Collect submissions
        - IN_TOURNAMENT: Monitor Celery progress
        - AWAITING_WEIGHTS: Set weights from DB results
        """
        state = self.get_tournament_state()
        
        if state == "PRE_TOURNAMENT":
            await self.collect_submissions()
            
        elif state == "IN_TOURNAMENT":
            bt.logging.debug("Tournament in progress - Celery evaluating submissions")
            await asyncio.sleep(5)
            
        elif state == "AWAITING_WEIGHTS":
            self.set_weights_from_results()
            
        else:  # DONE
            bt.logging.debug("Tournament completed and weights set. Waiting for next cycle.")
            await asyncio.sleep(5)

    def set_weights_from_results(self):
        """
        Poll DB for completed tournament results and set weights on-chain.
        
        This is called when validator detects a tournament in AWAITING_WEIGHTS state.
        """
        session = get_session()
        repo = TournamentRepository(session)
        
        try:
            tournament = repo.get_completed_tournament_awaiting_weights()
            
            if not tournament:
                bt.logging.debug("No completed tournament awaiting weights")
                return

            # Get final results from DB
            results = repo.get_results_by_tournament(tournament.id)
            
            if not results:
                bt.logging.warning(f"Tournament {tournament.id} completed but no results found")
                return

           # Build weight array from results
            weights = np.zeros(self.metagraph.n, dtype=np.float32)
            for result in results:
                if result.uid < len(weights):
                    weights[result.uid] = result.final_score

            # Normalize weights
            total = weights.sum()
            if total > 0:
                weights = weights / total

            bt.logging.info(f"Setting weights for tournament {tournament.id}: {len(results)} participants")

            # Process and set weights (using base class logic)
            from template.base.utils.weight_utils import (
                process_weights_for_netuid,
                convert_weights_and_uids_for_emit,
            )

            processed_weight_uids, processed_weights = process_weights_for_netuid(
                uids=self.metagraph.uids,
                weights=weights,
                netuid=self.config.netuid,
                subtensor=self.subtensor,
                metagraph=self.metagraph,
            )

            uint_uids, uint_weights = convert_weights_and_uids_for_emit(
                uids=processed_weight_uids, weights=processed_weights
            )

            # Set weights using validator's subtensor
            result, msg = self.subtensor.set_weights(
                wallet=self.wallet,
                netuid=self.config.netuid,
                uids=uint_uids,
                weights=uint_weights,
                wait_for_finalization=False,
                wait_for_inclusion=False,
                version_key=self.spec_version,
            )

            if result:
                # Mark tournament as weights_set in DB
                repo.mark_weights_set(tournament.id)
                bt.logging.info(f"✓ Weights set successfully for tournament {tournament.id}")
            else:
                bt.logging.error(f"✗ Failed to set weights for tournament {tournament.id}: {msg}")

        except Exception as e:
            bt.logging.error(f"Error setting weights from results: {e}")
        finally:
            session.close()

    def set_weights(self):
        """
        Override base class set_weights to use tournament results.
        
        Base class calls this periodically. We redirect to our polling logic.
        """
        self.set_weights_from_results()


if __name__ == "__main__":
    with Validator() as validator:
        bt.logging.info("Starting Analytics Tournament Validator")
        while True:
            time.sleep(5)
