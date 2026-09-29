"""Affective Congruence evaluation between verbal and embodied actions."""

import math
from typing import Any, Dict, List, Optional


class CongruenceEvaluator:
    """Evaluates affective congruence between spoken response and embodied actions."""

    # Valence polarity indicators (-1.0 to 1.0)
    VALENCE_MAP = {
        # Negative / defensive / withdrawal
        "defensive": -0.6, "crosses arms": -0.7, "looks away": -0.5, "clenches": -0.8,
        "sighs": -0.4, "rolls eyes": -0.8, "whispers nervously": -0.5, "withdraws": -0.7,
        "crying": -0.9, "frowns": -0.6, "stiffens": -0.6,
        # Neutral
        "pauses": 0.0, "blinks": 0.0, "nods slowly": 0.2, "shrugs": -0.2,
        # Positive / cooperative / open
        "smiles": 0.7, "makes eye contact": 0.6, "relaxes": 0.7, "nods": 0.5,
        "takes deep breath": 0.3, "unfolds arms": 0.6,
    }

    def _estimate_valence(self, text: str) -> float:
        """Heuristic valence estimation from text."""
        lower = text.lower()
        matched_scores = []
        for key, score in self.VALENCE_MAP.items():
            if key in lower:
                matched_scores.append(score)
        if not matched_scores:
            return 0.0
        return sum(matched_scores) / len(matched_scores)

    def evaluate_conversation(self, turns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compute S_congruence across turns with embodied actions."""
        congruence_scores: List[float] = []

        for turn in turns:
            verbal = turn.get("assistant", "")
            action = turn.get("assistant_embodied_action")
            if not action:
                continue

            v_val = self._estimate_valence(verbal)
            a_val = self._estimate_valence(action)

            # Cosine similarity in 1D/2D valence space or normalized absolute diff
            # Range mapped to [-1, 1], with 1 being identical direction
            if abs(v_val) < 1e-4 and abs(a_val) < 1e-4:
                sim = 1.0
            else:
                norm_v = abs(v_val) if abs(v_val) > 1e-4 else 0.1
                norm_a = abs(a_val) if abs(a_val) > 1e-4 else 0.1
                sim = (v_val * a_val) / (norm_v * norm_a)
            congruence_scores.append(sim)

        if not congruence_scores:
            return {
                "S_congruence": None,
                "embodied_turns_count": 0,
            }

        mean_cong = sum(congruence_scores) / len(congruence_scores)
        return {
            "S_congruence": round(mean_cong, 4),
            "embodied_turns_count": len(congruence_scores),
        }
