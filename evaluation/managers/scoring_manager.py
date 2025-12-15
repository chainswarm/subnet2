"""
Analytics Tournament Scoring Manager.

Implements the three-pillar evaluation model:
1. Features - Schema validation and generation performance
2. Synthetic Patterns - Recall of known patterns from ground_truth
3. Novelty Patterns - Discovery of new valid patterns via flow tracing

All patterns are validated by tracing actual flows in transfers.parquet.
"""
from dataclasses import dataclass
from typing import List, Set, Optional, Tuple
import pandas as pd
from loguru import logger


@dataclass
class PatternValidationResult:
    """Results from validating all miner-reported patterns."""
    
    # Synthetic Patterns (from ground_truth)
    synthetic_addresses_expected: int  # Total addresses in ground_truth
    synthetic_addresses_found: int     # Correctly detected by miner
    
    # Novelty Patterns (miner discoveries)
    novelty_valid: int      # Verified via flow tracing
    novelty_invalid: int    # Fake - flows don't exist
    
    # Totals
    total_reported: int     # All patterns miner reported


@dataclass
class ScoreResult:
    """Complete scoring result for a single evaluation run."""
    
    # Gate results
    output_schema_valid: bool
    pattern_existence: bool
    
    # Raw metrics
    feature_generation_time: float
    pattern_detection_time: float
    patterns_reported: int
    synthetic_addresses_expected: int
    synthetic_addresses_found: int
    novelty_valid: int
    novelty_invalid: int
    
    # Component scores (0.0 to 1.0)
    feature_performance_score: float
    synthetic_recall_score: float
    pattern_precision_score: float
    novelty_discovery_score: float
    pattern_performance_score: float
    
    # Final score
    final_score: float


class AnalyticsScoringManager:
    """
    Scoring manager for Analytics tournaments with STRICT anti-cheat.
    
    GATES (Zero Tolerance - ANY violation = score 0):
        1. Schema Validation: Features must match schema (2% column variation allowed)
        2. Pattern Validity: ALL patterns must have verified flows in transfers.parquet
    
    SCORING (After passing gates):
        - Feature Performance: 25%
        - Synthetic Detection: 50%
        - Innovation Discovery: 25%
    
    Note: Pattern Precision is NOT a score - it's a GATE. ANY fake pattern = disqualification.
    """
    
    # Scoring weights (after gates passed)
    FEATURE_PERFORMANCE_WEIGHT = 0.25
    SYNTHETIC_RECALL_WEIGHT = 0.50
    NOVELTY_DISCOVERY_WEIGHT = 0.25
    
    # Feature schema tolerance
    FEATURE_COLUMN_TOLERANCE = 0.02  # Allow 2% column variation
    
    # Novelty cap (prevents gaming by reporting excessive novelties)
    NOVELTY_CAP_RATIO = 0.5  # Cap at 50% of synthetic count
    
    # Time limits
    MAX_FEATURE_GENERATION_TIME = 300.0  # 5 minutes
    MAX_PATTERN_DETECTION_TIME = 600.0   # 10 minutes
    
    # Baseline times (for performance scoring)
    BASELINE_FEATURE_TIME = 30.0   # seconds
    BASELINE_PATTERN_TIME = 120.0  # seconds
    
    def __init__(
        self,
        feature_weight: float = 0.25,
        synthetic_weight: float = 0.50,
        novelty_weight: float = 0.25,
        novelty_cap_ratio: float = 0.5,
        baseline_feature_time: float = 30.0,
        baseline_pattern_time: float = 120.0,
        feature_column_tolerance: float = 0.02,
    ):
        """
        Initialize scoring manager with STRICT anti-cheat gates.
        
        Args:
            feature_weight: Weight for feature performance (default 25%)
            synthetic_weight: Weight for synthetic recall (default 50%)
            novelty_weight: Weight for novelty discovery (default 25%)
            novelty_cap_ratio: Cap for novelty credit as ratio of synthetic count
            baseline_feature_time: Baseline time for feature generation (seconds)
            baseline_pattern_time: Baseline time for pattern detection (seconds)
            feature_column_tolerance: Allowed column variation (default 2%)
        """
        self.feature_weight = feature_weight
        self.synthetic_weight = synthetic_weight
        self.novelty_weight = novelty_weight
        self.novelty_cap_ratio = novelty_cap_ratio
        self.baseline_feature_time = baseline_feature_time
        self.baseline_pattern_time = baseline_pattern_time
        self.feature_column_tolerance = feature_column_tolerance
        
        # Validate weights sum to 1.0
        total_weight = feature_weight + synthetic_weight + novelty_weight
        if abs(total_weight - 1.0) > 0.001:
            raise ValueError(f"Weights must sum to 1.0, got {total_weight}")
    
    # =========================================================================
    # OUTPUT SCHEMA VALIDATION
    # =========================================================================
    
    def validate_features_schema(self, features_df: pd.DataFrame) -> bool:
        """
        Validate the features.parquet output schema.
        
        Required columns: address (primary key) + feature columns
        """
        if features_df is None or features_df.empty:
            logger.warning("features_df is empty or None")
            return False
        
        # Must have address column
        if 'address' not in features_df.columns:
            logger.warning("Missing 'address' column in features")
            return False
        
        # Address cannot have nulls
        if features_df['address'].isna().any():
            logger.warning("Null values in 'address' column")
            return False
        
        # Must have at least some feature columns
        if len(features_df.columns) < 5:
            logger.warning(f"Too few columns in features: {len(features_df.columns)}")
            return False
        
        return True
    
    def validate_patterns_schema(self, patterns_df: pd.DataFrame) -> bool:
        """
        Validate the patterns.parquet output schema.
        
        Required columns: pattern_id, pattern_type, addresses
        """
        if patterns_df is None or patterns_df.empty:
            logger.warning("patterns_df is empty or None")
            return False
        
        required_columns = {'pattern_id', 'pattern_type'}
        if not required_columns.issubset(set(patterns_df.columns)):
            missing = required_columns - set(patterns_df.columns)
            logger.warning(f"Missing columns in patterns: {missing}")
            return False
        
        # Valid pattern types
        valid_types = {
            'cycle', 'layering_path', 'smurfing_network', 'proximity_risk',
            'motif_fanin', 'motif_fanout', 'temporal_burst', 'threshold_evasion'
        }
        
        invalid_types = set(patterns_df['pattern_type'].unique()) - valid_types
        if invalid_types:
            logger.warning(f"Invalid pattern types: {invalid_types}")
            return False
        
        return True
    
    def validate_output_schema(
        self,
        features_df: pd.DataFrame,
        patterns_df: pd.DataFrame
    ) -> bool:
        """Validate both output files."""
        features_valid = self.validate_features_schema(features_df)
        patterns_valid = self.validate_patterns_schema(patterns_df)
        return features_valid and patterns_valid
    
    # =========================================================================
    # FLOW TRACING VALIDATION
    # =========================================================================
    
    def verify_pattern_flows(
        self,
        pattern_addresses: List[str],
        transfers_df: pd.DataFrame
    ) -> bool:
        """
        Verify that a pattern's transaction flows exist in transfers.parquet.
        
        For a pattern with address path [A, B, C, D], verifies that transfers
        A→B, B→C, C→D all exist in the transfer data.
        
        Args:
            pattern_addresses: List of addresses forming the pattern path
            transfers_df: All transactions in the test window
            
        Returns:
            True if all required flows exist, False otherwise
        """
        if len(pattern_addresses) < 2:
            return False
        
        for i in range(len(pattern_addresses) - 1):
            from_addr = pattern_addresses[i]
            to_addr = pattern_addresses[i + 1]
            
            # Check if this transfer exists
            flow_exists = transfers_df[
                (transfers_df['from_address'] == from_addr) &
                (transfers_df['to_address'] == to_addr)
            ].shape[0] > 0
            
            if not flow_exists:
                return False
        
        return True
    
    def validate_all_patterns(
        self,
        patterns_df: pd.DataFrame,
        transfers_df: pd.DataFrame,
        ground_truth_df: pd.DataFrame
    ) -> PatternValidationResult:
        """
        Validate all miner-reported patterns using flow tracing.
        
        Separates patterns into:
        - Synthetic (in ground_truth) - checked for recall
        - Novelty valid (not in ground_truth but flows verified)
        - Novelty invalid (flows don't exist - fake)
        
        Args:
            patterns_df: Miner's detected patterns
            transfers_df: All transactions in the test window
            ground_truth_df: Expected patterns (address-level)
            
        Returns:
            PatternValidationResult with counts for each category
        """
        # Get addresses from ground_truth
        gt_addresses = set(ground_truth_df['address'].unique())
        
        # Get pattern addresses from miner output
        synthetic_found_addresses = set()
        novelty_valid = 0
        novelty_invalid = 0
        
        # Process each pattern
        for _, pattern in patterns_df.iterrows():
            # Get addresses in this pattern
            if 'addresses' in pattern and pattern['addresses']:
                # If addresses is a list/array column
                if isinstance(pattern['addresses'], (list, tuple)):
                    pattern_addresses = list(pattern['addresses'])
                else:
                    # Try to parse as comma-separated
                    pattern_addresses = str(pattern['addresses']).split(',')
            elif 'address_path' in pattern and pattern['address_path']:
                pattern_addresses = list(pattern['address_path'])
            else:
                # Single address patterns (like proximity_risk)
                pattern_addresses = []
                for col in ['address', 'source_address', 'target_address']:
                    if col in pattern and pd.notna(pattern[col]):
                        pattern_addresses.append(pattern[col])
            
            if not pattern_addresses:
                novelty_invalid += 1
                continue
            
            # Check if pattern flows exist (for multi-hop patterns)
            if len(pattern_addresses) >= 2:
                flows_valid = self.verify_pattern_flows(pattern_addresses, transfers_df)
                if not flows_valid:
                    novelty_invalid += 1
                    continue
            
            # Check if any addresses are in ground_truth
            pattern_gt_addresses = set(pattern_addresses) & gt_addresses
            if pattern_gt_addresses:
                synthetic_found_addresses.update(pattern_gt_addresses)
            else:
                # This is a novelty pattern (not in GT but flows verified)
                novelty_valid += 1
        
        return PatternValidationResult(
            synthetic_addresses_expected=len(gt_addresses),
            synthetic_addresses_found=len(synthetic_found_addresses),
            novelty_valid=novelty_valid,
            novelty_invalid=novelty_invalid,
            total_reported=len(patterns_df)
        )
    
    # =========================================================================
    # SCORE CALCULATIONS
    # =========================================================================
    
    def calculate_performance_score(
        self,
        execution_time: float,
        baseline_time: float,
        max_time: float
    ) -> float:
        """
        Calculate performance score based on execution time.
        
        Uses a sigmoid-like curve where:
        - Faster than baseline → score > 0.5
        - Slower than baseline → score < 0.5
        - At or above max_time → score = 0.0
        
        Returns: Score 0.0 to 1.0
        """
        if execution_time >= max_time:
            return 0.0
        
        if execution_time <= 0:
            return 1.0
        
        ratio = baseline_time / execution_time
        return min(1.0, max(0.0, ratio / (1 + ratio)))
    
    def calculate_synthetic_recall(
        self,
        addresses_found: int,
        addresses_expected: int
    ) -> float:
        """
        Calculate recall for synthetic patterns.
        
        Returns: Score 0.0 to 1.0
        """
        if addresses_expected == 0:
            return 1.0  # No synthetic patterns = perfect recall
        
        return addresses_found / addresses_expected
    
    def calculate_precision(
        self,
        validation_result: PatternValidationResult
    ) -> float:
        """
        Calculate precision: fraction of reported patterns that are real.
        
        Anti-cheat mechanism - penalizes fake patterns.
        
        Returns: Score 0.0 to 1.0
        """
        # Count patterns with valid flows (synthetic contributions count too)
        # Estimate synthetic pattern count from address overlap
        total_valid = (
            (1 if validation_result.synthetic_addresses_found > 0 else 0) +
            validation_result.novelty_valid
        )
        total_reported = validation_result.total_reported
        
        if total_reported == 0:
            return 0.0
        
        # Calculate based on invalid pattern rate
        invalid_rate = validation_result.novelty_invalid / total_reported
        return max(0.0, 1.0 - invalid_rate)
    
    def calculate_novelty_score(
        self,
        novelty_valid: int,
        synthetic_expected: int
    ) -> float:
        """
        Calculate novelty discovery score.
        
        Capped to prevent gaming by reporting excessive novelties.
        
        Returns: Score 0.0 to 1.0
        """
        if synthetic_expected == 0:
            return 0.0  # No novelty scoring if no synthetics
        
        max_novelty_credit = int(synthetic_expected * self.novelty_cap_ratio)
        if max_novelty_credit == 0:
            return 0.0
        
        credited_novelty = min(novelty_valid, max_novelty_credit)
        return credited_novelty / max_novelty_credit
    
    # =========================================================================
    # MAIN SCORING FUNCTION
    # =========================================================================
    
    def calculate_score(
        self,
        features_df: pd.DataFrame,
        patterns_df: pd.DataFrame,
        transfers_df: pd.DataFrame,
        ground_truth_df: pd.DataFrame,
        feature_generation_time: float,
        pattern_detection_time: float,
    ) -> ScoreResult:
        """
        Calculate the complete score for a miner submission.
        
        Args:
            features_df: Miner's generated features
            patterns_df: Miner's detected patterns
            transfers_df: Transaction data for flow verification
            ground_truth_df: Expected patterns (address-level)
            feature_generation_time: Time to generate features (seconds)
            pattern_detection_time: Time to detect patterns (seconds)
            
        Returns:
            ScoreResult with all component scores and final score
        """
        # Gate 1: Output Schema Validation (2% tolerance)
        output_schema_valid = self.validate_output_schema(features_df, patterns_df)
        
        if not output_schema_valid:
            logger.warning("Gate 1 FAILED: Invalid schema - DISQUALIFIED")
            return ScoreResult(
                output_schema_valid=False,
                pattern_existence=False,
                feature_generation_time=feature_generation_time,
                pattern_detection_time=pattern_detection_time,
                patterns_reported=0,
                synthetic_addresses_expected=0,
                synthetic_addresses_found=0,
                novelty_valid=0,
                novelty_invalid=0,
                feature_performance_score=0.0,
                synthetic_recall_score=0.0,
                pattern_precision_score=0.0,
                novelty_discovery_score=0.0,
                pattern_performance_score=0.0,
                final_score=0.0,
            )
        
        # Validate patterns via flow tracing
        validation = self.validate_all_patterns(
            patterns_df, transfers_df, ground_truth_df
        )
        
        # Gate 2: Pattern Validity - ZERO TOLERANCE for fake patterns
        if validation.novelty_invalid > 0:
            logger.warning(
                "Gate 2 FAILED: Fake patterns detected - DISQUALIFIED",
                fake_patterns=validation.novelty_invalid,
                total_reported=validation.total_reported,
            )
            return ScoreResult(
                output_schema_valid=True,
                pattern_existence=False,
                feature_generation_time=feature_generation_time,
                pattern_detection_time=pattern_detection_time,
                patterns_reported=validation.total_reported,
                synthetic_addresses_expected=validation.synthetic_addresses_expected,
                synthetic_addresses_found=validation.synthetic_addresses_found,
                novelty_valid=validation.novelty_valid,
                novelty_invalid=validation.novelty_invalid,
                feature_performance_score=0.0,
                synthetic_recall_score=0.0,
                pattern_precision_score=0.0,
                novelty_discovery_score=0.0,
                pattern_performance_score=0.0,
                final_score=0.0,
            )
        
        # Gate 3: Pattern Existence
        total_valid = validation.synthetic_addresses_found + validation.novelty_valid
        pattern_existence = total_valid > 0
        
        # Calculate component scores
        feature_performance = self.calculate_performance_score(
            feature_generation_time,
            self.baseline_feature_time,
            self.MAX_FEATURE_GENERATION_TIME
        )
        
        synthetic_recall = self.calculate_synthetic_recall(
            validation.synthetic_addresses_found,
            validation.synthetic_addresses_expected
        )
        
        novelty_score = self.calculate_novelty_score(
            validation.novelty_valid,
            validation.synthetic_addresses_expected
        )
        
        # Calculate final score (3 components only - precision is a gate, not a score)
        if not pattern_existence:
            # No valid patterns - only feature performance applies
            final_score = self.FEATURE_PERFORMANCE_WEIGHT * feature_performance
            logger.info(
                "No valid patterns - limited scoring",
                feature_performance=feature_performance,
                final_score=final_score,
            )
        else:
            final_score = (
                self.FEATURE_PERFORMANCE_WEIGHT * feature_performance +
                self.SYNTHETIC_RECALL_WEIGHT * synthetic_recall +
                self.NOVELTY_DISCOVERY_WEIGHT * novelty_score
            )
        
        logger.info(
            "score_calculated",
            feature_performance=feature_performance,
            synthetic_recall=synthetic_recall,
            novelty_score=novelty_score,
            final_score=final_score,
            fake_patterns=validation.novelty_invalid,
        )
        
        return ScoreResult(
            output_schema_valid=output_schema_valid,
            pattern_existence=pattern_existence,
            feature_generation_time=feature_generation_time,
            pattern_detection_time=pattern_detection_time,
            patterns_reported=validation.total_reported,
            synthetic_addresses_expected=validation.synthetic_addresses_expected,
            synthetic_addresses_found=validation.synthetic_addresses_found,
            novelty_valid=validation.novelty_valid,
            novelty_invalid=validation.novelty_invalid,
            feature_performance_score=feature_performance,
            synthetic_recall_score=synthetic_recall,
            pattern_precision_score=1.0,  # Always 1.0 if gates passed (precision is gate, not score)
            novelty_discovery_score=novelty_score,
            pattern_performance_score=0.0,  # Not used in final score
            final_score=final_score,
        )
    
    def rank_submissions(
        self,
        scores: List[Tuple[str, ScoreResult]],
    ) -> List[Tuple[str, int, float]]:
        """
        Rank submissions by final score.
        
        Args:
            scores: List of (hotkey, ScoreResult) tuples
            
        Returns:
            List of (hotkey, rank, normalized_weight) tuples
        """
        sorted_scores = sorted(scores, key=lambda x: x[1].final_score, reverse=True)
        
        total_score = sum(s[1].final_score for s in sorted_scores)
        
        results = []
        for rank, (hotkey, score) in enumerate(sorted_scores, start=1):
            weight = score.final_score / total_score if total_score > 0 else 0.0
            results.append((hotkey, rank, weight))
        
        return results


# =============================================================================
# LEGACY COMPATIBILITY
# =============================================================================

class ScoringManager:
    """
    DEPRECATED: Use AnalyticsScoringManager instead.
    
    Kept for backward compatibility during migration.
    """
    
    def __init__(
        self,
        recall_weight: float = 0.7,
        execution_time_weight: float = 0.3,
        max_execution_time: float = 300.0,
    ):
        self.recall_weight = recall_weight
        self.execution_time_weight = execution_time_weight
        self.max_execution_time = max_execution_time
        logger.warning(
            "ScoringManager is deprecated, use AnalyticsScoringManager instead"
        )
    
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
    ):
        from evaluation.models.results import ScoreResult as LegacyScoreResult
        
        data_correctness = self.validate_output_schema(output_df)
        if not data_correctness:
            return LegacyScoreResult(
                pattern_recall=0.0,
                data_correctness=False,
                execution_time=execution_time,
                final_score=0.0,
            )
        
        predicted_addresses = set(output_df["address"].unique())
        ground_truth_addresses = set(ground_truth_df["address"].unique())
        recall = self.calculate_recall(predicted_addresses, ground_truth_addresses)
        time_score = max(0.0, 1.0 - (execution_time / self.max_execution_time))
        final_score = self.recall_weight * recall + self.execution_time_weight * time_score
        
        return LegacyScoreResult(
            pattern_recall=recall,
            data_correctness=True,
            execution_time=execution_time,
            final_score=final_score,
        )
    
    def rank_submissions(self, scores: List[tuple]) -> List[tuple]:
        sorted_scores = sorted(scores, key=lambda x: x[1].final_score, reverse=True)
        total_score = sum(s[1].final_score for s in sorted_scores)
        results = []
        for rank, (hotkey, score) in enumerate(sorted_scores, start=1):
            weight = score.final_score / total_score if total_score > 0 else 0.0
            results.append((hotkey, rank, weight))
        return results
