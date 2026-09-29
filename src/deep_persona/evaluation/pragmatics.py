"""Pragmatics fluidity, self-repetition, and echolalia evaluation."""

from typing import Any, Dict, List
from rouge_score import rouge_scorer


class PragmaticsEvaluator:
    """Computes S_pragmatics, S_overlap, S_self, and Echoing rate using Rouge-L."""

    def __init__(
        self,
        window_size: int = 5,
        tau_echo: float = 0.65,
        alpha: float = 0.33,
        beta: float = 0.33,
        gamma: float = 0.33,
    ):
        self.window_size = window_size
        self.tau_echo = tau_echo
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)

    def _rouge_l_f1(self, target: str, prediction: str) -> float:
        """Compute ROUGE-L F1 score between two texts."""
        if not target.strip() or not prediction.strip():
            return 0.0
        scores = self.scorer.score(target, prediction)
        return float(scores["rougeL"].fmeasure)

    def evaluate_conversation(self, turns: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Evaluate pragmatics across all turns in a conversation.
        Each turn dict must have 'user' and 'assistant' keys.
        """
        if not turns:
            return {
                "S_pragmatics": 1.0,
                "S_overlap_mean": 0.0,
                "S_self_mean": 0.0,
                "echo_rate": 0.0,
            }

        overlap_scores: List[float] = []
        self_rep_scores: List[float] = []
        echo_indicators: List[float] = []
        assistant_history: List[str] = []

        for turn_idx, turn in enumerate(turns):
            user_text = turn.get("user", "")
            asst_text = turn.get("assistant", "")

            # 1. User overlap score
            overlap = self._rouge_l_f1(user_text, asst_text)
            overlap_scores.append(overlap)

            # 2. Self repetition penalty over window n
            window_start = max(0, turn_idx - self.window_size)
            past_window = assistant_history[window_start:turn_idx]
            if past_window:
                self_score = max(self._rouge_l_f1(prev, asst_text) for prev in past_window)
            else:
                self_score = 0.0
            self_rep_scores.append(self_score)

            # 3. Echo indicator
            is_echo = 1.0 if overlap > self.tau_echo else 0.0
            echo_indicators.append(is_echo)

            assistant_history.append(asst_text)

        mean_overlap = sum(overlap_scores) / len(overlap_scores)
        mean_self = sum(self_rep_scores) / len(self_rep_scores)
        echo_rate = sum(echo_indicators) / len(echo_indicators)

        penalty = (self.alpha * mean_overlap) + (self.beta * mean_self) + (self.gamma * echo_rate)
        s_pragmatics = max(0.0, min(1.0, 1.0 - penalty))

        return {
            "S_pragmatics": round(s_pragmatics, 4),
            "S_overlap_mean": round(mean_overlap, 4),
            "S_self_mean": round(mean_self, 4),
            "echo_rate": round(echo_rate, 4),
        }
