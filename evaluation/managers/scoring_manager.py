from typing import List, Set

import pandas as pd
from loguru import logger

from evaluation.models.results import ScoreResult


class ScoringManager:
    def __init__(
        self,
        recall_weight: float = 0.7,
        execution_time_weight: float = 0.3,
        max_execution_time: float = 300.0,
    ):
        self.recall_weight = recall_weight
        self.execution_time_weight = execution_time_weight
        self.max_execution_time = max_execution_time

    def calculate_recall(
        self,
        predicted_addresses: Set[str],
        ground_truth_addresses: Set[str],
    ) -> float:
        if not ground_truth_addresses:
            return 0.0

        true_positives = len(predicted_addresses & ground_truth_addresses)
        return true_positives / len(ground_truth_addresses)

    def validate_output_schema(self, output_df: pd.DataFrame) -> bool:
        required_columns = {"address", "pattern_type", "confidence"}
        if not required_columns.issubset(set(output_df.columns)):
            return False

        if not pd.api.types.is_numeric_dtype(output_df["confidence"]):
            return False

        if (output_df["confidence"] < 0).any() or (output_df["confidence"] > 1).any():
            return False

        return True

    def calculate_score(
        self,
        output_df: pd.DataFrame,
        ground_truth_df: pd.DataFrame,
        execution_time: float,
    ) -> ScoreResult:
        data_correctness = self.validate_output_schema(output_df)
        if not data_correctness:
            logger.warning("invalid_output_schema")
            return ScoreResult(
                pattern_recall=0.0,
                data_correctness=False,
                execution_time=execution_time,
                final_score=0.0,
            )

        predicted_addresses = set(output_df["address"].unique())
        ground_truth_addresses = set(ground_truth_df["address"].unique())

        recall = self.calculate_recall(predicted_addresses, ground_truth_addresses)

        time_score = max(0.0, 1.0 - (execution_time / self.max_execution_time))

        final_score = (
            self.recall_weight * recall +
            self.execution_time_weight * time_score
        )

        logger.info(
            "score_calculated",
            recall=recall,
            time_score=time_score,
            final_score=final_score,
        )

        return ScoreResult(
            pattern_recall=recall,
            data_correctness=True,
            execution_time=execution_time,
            final_score=final_score,
        )

    def rank_submissions(
        self,
        scores: List[tuple],
    ) -> List[tuple]:
        sorted_scores = sorted(scores, key=lambda x: x[1].final_score, reverse=True)

        total_score = sum(s[1].final_score for s in sorted_scores)

        results = []
        for rank, (hotkey, score) in enumerate(sorted_scores, start=1):
            weight = score.final_score / total_score if total_score > 0 else 0.0
            results.append((hotkey, rank, weight))

        return results
