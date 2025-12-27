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

import typing
import re
import bittensor as bt

class SubmissionSynapse(bt.Synapse):
    """
    Synapse for miner tournament submissions.
    
    Validators use this to query miners for their code repository information.
    Miners respond with their repository URL and commit hash, which validators
    then use to clone, build, and evaluate the miner's analyzer.
    
    Attributes:
        tournament_id: UUID of the tournament
        epoch_number: Current epoch number
        repository_url: GitHub repository URL (HTTPS format)
        commit_hash: Git commit SHA or branch name
    """
    tournament_id: str
    epoch_number: int

    repository_url: typing.Optional[str] = None
    commit_hash: typing.Optional[str] = None

    def deserialize(self) -> "SubmissionSynapse":
        """
        Return self for strong typing in validator.
        
        This provides better type hints and allows validators to access
        all synapse metadata (dendrite info, timing, etc.) rather than
        just the submission data fields.
        
        Returns:
            Self (SubmissionSynapse object)
        """
        return self

    @staticmethod
    def validate_submission_data(
        repository_url: typing.Optional[str],
        commit_hash: typing.Optional[str]
    ) -> typing.Tuple[bool, typing.Optional[str]]:
        """
        Validate submission data fields (format validation only).
        
        This performs format validation to fail fast on invalid input.
        Repository existence is validated later during git clone operation.
        
        Validation rules:
        - Both fields must be non-empty strings
        - repository_url must be a valid GitHub HTTPS URL
        - commit_hash can be either a Git SHA (7-40 hex chars) or branch name
        
        Args:
            repository_url: GitHub repository URL to validate
            commit_hash: Git commit SHA or branch name to validate
            
        Returns:
            Tuple of (is_valid, error_message)
            - (True, None) if valid
            - (False, error_message) if invalid
        
        Examples:
            >>> SubmissionSynapse.validate_submission_data(
            ...     "https://github.com/user/repo",
            ...     "abc123def"
            ... )
            (True, None)
            
            >>> SubmissionSynapse.validate_submission_data(
            ...     "https://github.com/user/repo",
            ...     "main"
            ... )
            (True, None)
            
            >>> SubmissionSynapse.validate_submission_data(
            ...     "git@github.com:user/repo.git",
            ...     "abc123"
            ... )
            (False, "repository_url must be a GitHub HTTPS URL (https://github.com/owner/repo)")
        """
        # 1. Check existence
        if not repository_url or not commit_hash:
            return False, "Missing repository_url or commit_hash"
        
        # 2. Validate types
        if not isinstance(repository_url, str):
            return False, "repository_url must be a string"
        
        if not isinstance(commit_hash, str):
            return False, "commit_hash must be a string"
        
        # 3. Validate GitHub HTTPS URL format
        repository_url = repository_url.strip()
        
        # GitHub HTTPS pattern: https://github.com/owner/repo (with optional .git)
        github_https_pattern = r'^https://github\.com/[\w-]+/[\w.-]+(?:\.git)?$'
        
        if not re.match(github_https_pattern, repository_url):
            return False, "repository_url must be a GitHub HTTPS URL (https://github.com/owner/repo)"
        
        # 4. Validate commit hash format
        # Allow both Git SHA (7-40 hex chars) and branch names
        commit_hash = commit_hash.strip()
        
        # Git SHA pattern: 7-40 hexadecimal characters
        is_sha = re.match(r'^[0-9a-fA-F]{7,40}$', commit_hash)
        
        # Branch name pattern: alphanumeric, hyphens, underscores, slashes (max 255 chars)
        # Common examples: main, develop, feature/new-algo, release/v1.0
        is_branch = re.match(r'^[\w\-./]{1,255}$', commit_hash)
        
        if not (is_sha or is_branch):
            return False, "commit_hash must be a valid Git SHA (7-40 hex chars) or branch name"
        
        return True, None

    def is_valid_submission(self) -> typing.Tuple[bool, typing.Optional[str]]:
        """
        Validate this synapse's submission data.
        
        Convenience instance method that validates the synapse's own
        repository_url and commit_hash fields.
        
        Returns:
            Tuple of (is_valid, error_message)
        
        Example:
            >>> synapse = SubmissionSynapse(
            ...     tournament_id="abc",
            ...     epoch_number=1,
            ...     repository_url="https://github.com/user/repo",
            ...     commit_hash="main"
            ... )
            >>> synapse.is_valid_submission()
            (True, None)
        """
        return self.validate_submission_data(self.repository_url, self.commit_hash)
