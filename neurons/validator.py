# The MIT License (MIT)
# Copyright © 2023 Yuma Rao
# TODO(developer): Set your name
# Copyright © 2023 <your name>

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the “Software”), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.


import asyncio
import time

# Bittensor
import bittensor as bt

# import base validator class which takes care of most of the boilerplate
from template.base.validator import BaseValidatorNeuron


class Validator(BaseValidatorNeuron):
    """
    Analytics Tournament Validator - Tournament-Only Mode.
    
    This validator operates exclusively via tournament-based evaluation:
    - epoch_start_task (00:00 UTC): Collects submissions via SubmissionSynapse
    - evaluation_task (hourly): Runs and scores containers across 5 days × 3 networks
    - epoch_end_task (23:00 UTC): Calculates rankings, sets weights on-chain
    
    The validator does NOT perform standard forward passes or set weights directly.
    All evaluation logic is handled by Celery background tasks.
    """

    def __init__(self, config=None):
        super(Validator, self).__init__(config=config)

        bt.logging.info("load_state()")
        self.load_state()

        bt.logging.info("Analytics Tournament Validator initialized - tournament-only mode")

    async def forward(self):
        """
        Tournament-only validator - NO standard forward pass.
        
        All tournament logic is handled by Celery tasks:
        - epoch_start_task (00:00): Collect submissions via SubmissionSynapse
        - evaluation_task (hourly): Run and score containers
        - epoch_end_task (23:00): Calculate rankings, set weights
        
        This validator just maintains metagraph sync and serves axon for SubmissionSynapse.
        """
        from evaluation.repositories.tournament_repository import TournamentRepository
        from evaluation.db import get_session
        
        session = get_session()
        repo = TournamentRepository(session)
        
        try:
            tournament = repo.get_active_tournament()
            
            if tournament:
                bt.logging.debug(
                    f"Analytics tournament epoch {tournament.epoch_number} "
                    f"status={tournament.status} - managed by Celery tasks"
                )
            else:
                bt.logging.debug("No active tournament - waiting for epoch_start_task")
            
            # Sleep to maintain event loop
            await asyncio.sleep(5)
            
        except Exception as e:
            bt.logging.error(f"Error checking tournament status: {e}")
            await asyncio.sleep(5)
            
        finally:
            session.close()

    def set_weights(self):
        """
        Override to prevent weight setting conflicts.
        
        Analytics tournaments: Weights set by epoch_end_task ONLY.
        This validator does NOT set weights via standard loop.
        """
        from evaluation.repositories.tournament_repository import TournamentRepository
        from evaluation.db import get_session
        
        session = get_session()
        repo = TournamentRepository(session)
        
        try:
            tournament = repo.get_active_tournament()
            
            if tournament:
                bt.logging.info(
                    f"Tournament epoch {tournament.epoch_number} active - "
                    f"weights managed by epoch_end_task. Skipping standard weight setting."
                )
                return
            
            # No tournament - but analytics subnet is tournament-only
            bt.logging.info("No active tournament - weights will be set by epoch_end_task when tournament completes")
            
        except Exception as e:
            bt.logging.error(f"Error checking tournament for weight setting: {e}")
            
        finally:
            session.close()


if __name__ == "__main__":
    with Validator() as validator:
        bt.logging.info(f"Starting the Validator")
        while True:
            bt.logging.info(f"Validator running... {time.time()}")
            time.sleep(5)
