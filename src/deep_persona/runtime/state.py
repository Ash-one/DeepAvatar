"""Persona runtime state definition."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Set


@dataclass
class PersonaState:
    stage: str = "guarded"
    trust: float = 0.2
    defensiveness: float = 0.8
    engagement: float = 0.4
    turn: int = 0
    revealed_information: Set[str] = field(default_factory=set)

    def clamp(self) -> None:
        """Clamp all psychological scalars to [0.0, 1.0]."""
        self.trust = max(0.0, min(1.0, float(self.trust)))
        self.defensiveness = max(0.0, min(1.0, float(self.defensiveness)))
        self.engagement = max(0.0, min(1.0, float(self.engagement)))

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to serializable dictionary."""
        return {
            "stage": self.stage,
            "trust": round(self.trust, 4),
            "defensiveness": round(self.defensiveness, 4),
            "engagement": round(self.engagement, 4),
            "turn": self.turn,
            "revealed_information": sorted(list(self.revealed_information)),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PersonaState":
        """Instantiate state from dictionary."""
        return cls(
            stage=data.get("stage", "guarded"),
            trust=data.get("trust", 0.2),
            defensiveness=data.get("defensiveness", 0.8),
            engagement=data.get("engagement", 0.4),
            turn=data.get("turn", 0),
            revealed_information=set(data.get("revealed_information", [])),
        )

    @classmethod
    def create_for_persona(cls, persona: Any) -> "PersonaState":
        """Instantiate initial state using persona-specific baseline and dynamics."""
        dyn = getattr(persona, "dynamics", None)
        stage = getattr(dyn, "initial_stage", "guarded") if dyn else "guarded"
        baseline = getattr(dyn, "baseline", None) if dyn else None
        if baseline is not None:
            return cls(
                stage=stage,
                trust=float(getattr(baseline, "trust", 0.2)),
                defensiveness=float(getattr(baseline, "defensiveness", 0.8)),
                engagement=float(getattr(baseline, "engagement", 0.4)),
            )
        return cls(stage=stage)
