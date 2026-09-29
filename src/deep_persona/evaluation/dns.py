"""Dialogue Naturalness Score (DNS) calculation using Mahalanobis Distance."""

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union
import numpy as np
from scipy.stats import chi2

DEFAULT_BASELINE_DIR = Path(__file__).resolve().parents[3] / "data" / "human_baseline"

# Default benchmark distribution estimates from DailyDialog & CounselChat human conversations
DEFAULT_HUMAN_STATS = {
    "dailydialog": {
        "mean": [0.82, 0.78, 0.08],  # [S_pragmatics, S_joint, S_emotion]
        "cov": [
            [0.015, 0.004, 0.001],
            [0.004, 0.020, 0.002],
            [0.001, 0.002, 0.005],
        ],
    },
    "counselchat": {
        "mean": [0.85, 0.88, 0.14],
        "cov": [
            [0.012, 0.003, 0.002],
            [0.003, 0.018, 0.003],
            [0.002, 0.003, 0.008],
        ],
    },
    "combined": {
        "mean": [0.835, 0.83, 0.11],
        "cov": [
            [0.014, 0.0035, 0.0015],
            [0.0035, 0.019, 0.0025],
            [0.0015, 0.0025, 0.0065],
        ],
    },
}


class DNSEvaluator:
    """Computes Mahalanobis Distance, p-value, and DNS against human baselines."""

    def __init__(
        self,
        baseline_name: str = "combined",
        baseline_dir: Optional[Path] = None,
        lambda_param: float = 0.089,
    ):
        self.baseline_name = baseline_name
        self.baseline_dir = baseline_dir or DEFAULT_BASELINE_DIR
        self.lambda_param = lambda_param
        self.mean, self.cov_inv = self._load_baseline(baseline_name)

    def _load_baseline(self, name: str) -> Tuple[np.ndarray, np.ndarray]:
        """Load baseline stats JSON or fallback to defaults."""
        file_path = self.baseline_dir / f"{name}_stats.json"
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                mean = np.array(data["mean"], dtype=float)
                cov = np.array(data["cov"], dtype=float)
        else:
            stats = DEFAULT_HUMAN_STATS.get(name, DEFAULT_HUMAN_STATS["combined"])
            mean = np.array(stats["mean"], dtype=float)
            cov = np.array(stats["cov"], dtype=float)

        # Invert covariance matrix (with small regularization for numerical stability)
        cov_reg = cov + np.eye(len(mean)) * 1e-6
        cov_inv = np.linalg.inv(cov_reg)
        return mean, cov_inv

    def compute_dns(
        self,
        s_pragmatics: float,
        s_joint: float,
        s_emotion: float,
    ) -> Dict[str, float]:
        """
        Calculate Mahalanobis distance, DNS score, and chi-squared p-value.
        Vector: x = [s_pragmatics, s_joint, s_emotion]
        """
        x = np.array([s_pragmatics, s_joint, s_emotion], dtype=float)
        diff = x - self.mean
        d_m_sq = float(diff.T @ self.cov_inv @ diff)
        d_m = float(np.sqrt(max(0.0, d_m_sq)))

        dns_score = float(np.exp(-self.lambda_param * d_m_sq))
        # Chi-squared CDF with df = 3
        p_val = float(1.0 - chi2.cdf(d_m_sq, df=3))

        return {
            f"DNS_{self.baseline_name}": round(dns_score, 4),
            "mahalanobis_distance": round(d_m, 4),
            "p_value": round(p_val, 4),
        }
