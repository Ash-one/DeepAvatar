"""Pydantic schemas for Episodic, Semantic, Relationship memories, Worldview Anchors, and Epistemic Horizons."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator



class EpisodicMemory(BaseModel):
    """A concrete autobiographical episode directly experienced by the character."""
    id: str
    period: Optional[str] = None  # e.g. "childhood", "sect_days", "recent"
    timestamp_order: int = 0
    summary: str
    details: str = ""
    emotional_valence: Optional[str] = None  # e.g. "shame", "dread", "wonder"
    participants: List[str] = Field(default_factory=list)
    evidence_id: Optional[str] = None  # Grounding reference to Phase A evidence ID


class SemanticMemory(BaseModel):
    """Subjective conceptual understanding and worldview knowledge."""
    id: str
    concept: str
    understanding: str


class RelationshipMemory(BaseModel):
    """Interpersonal stance and memory of interactions with a specific character or role."""
    id: str
    target_character: str
    relation: str  # e.g. "father", "sect_elder", "classmate", "stranger"
    stance: str = ""  # e.g. "terrified of displeasing", "reverent", "guarded"
    shared_history_summary: str = ""


class WorldviewAnchor(BaseModel):
    """Ontological and cosmological coordinate system defining the character's universe."""
    universe: str = "real_world"  # e.g. "昭和初年日本", "修仙界 (九洲)", "夜之城 (Cyberpunk 2077)"
    world_type: str = "historical"  # historical, fictional_fantasy, fictional_scifi, contemporary, custom
    epoch_or_timeline: str = "present"  # e.g. "昭和5年 (1930)", "宗门大比前夕", "第三纪元3018年"
    spatial_scope: List[str] = Field(default_factory=list)  # e.g. ["中州", "东海万剑宗"] or ["青森", "东京"]
    rules_of_reality: str = "Standard physical laws; no supernatural magic or futuristic sci-fi."


class EpistemicHorizon(BaseModel):
    """Closed-world epistemic boundary and defamiliarization rules for both historical and fictional universes."""
    worldview: WorldviewAnchor = Field(default_factory=WorldviewAnchor)
    closed_world_axiom: bool = True
    known_domains: List[str] = Field(default_factory=list)
    defamiliarization_strategy: str = (
        "When encountering concepts alien to your worldview, epoch, or domain, do NOT understand their modern/out-of-world meaning. "
        "Interpret them through your character's cultural lens, treat them as bizarre foreign gibberish, or question if the interlocutor is mocking you."
    )
    unrecorded_event_strategy: str = (
        "Any past event or shared memory claimed by the interlocutor that is absent from your autobiographical memory never occurred in your reality. "
        "Reject it firmly as an illusion, confusion, or lie."
    )


class PerspectiveBoundary(BaseModel):
    """Legacy perspective boundary schema maintained for backward compatibility."""
    temporal_horizon: str = "present"
    persona_knows: List[str] = Field(default_factory=list)
    persona_does_not_know: List[str] = Field(default_factory=list)
    hallucination_defense_strategy: str = (
        "Strictly refuse ungrounded memories or anachronistic facts. "
        "React with natural character confusion or guarded rejection."
    )


class MemoryConfig(BaseModel):
    """Encapsulates the complete memory and epistemic horizon specification for a persona."""
    epistemic_horizon: EpistemicHorizon = Field(default_factory=EpistemicHorizon)
    perspective_boundary: Optional[PerspectiveBoundary] = None
    episodic_memories: List[EpisodicMemory] = Field(default_factory=list)
    relationship_memories: List[RelationshipMemory] = Field(default_factory=list)
    semantic_memories: List[SemanticMemory] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _harmonize_horizon_and_boundary(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # If perspective_boundary provided without epistemic_horizon, populate epistemic_horizon
            if "perspective_boundary" in data and "epistemic_horizon" not in data:
                pb = data.get("perspective_boundary", {})
                if isinstance(pb, dict):
                    data["epistemic_horizon"] = {
                        "worldview": {
                            "universe": pb.get("temporal_horizon", "historical"),
                            "world_type": "historical",
                            "epoch_or_timeline": pb.get("temporal_horizon", "present"),
                        },
                        "known_domains": pb.get("persona_knows", []),
                        "defamiliarization_strategy": pb.get("hallucination_defense_strategy", ""),
                    }
            # Conversely if epistemic_horizon provided, sync perspective_boundary for legacy consumers
            elif "epistemic_horizon" in data and "perspective_boundary" not in data:
                eh = data.get("epistemic_horizon", {})
                if isinstance(eh, dict):
                    wv = eh.get("worldview", {})
                    data["perspective_boundary"] = {
                        "temporal_horizon": wv.get("epoch_or_timeline", "present"),
                        "persona_knows": eh.get("known_domains", []),
                        "persona_does_not_know": [],
                        "hallucination_defense_strategy": eh.get("defamiliarization_strategy", ""),
                    }
        return data
