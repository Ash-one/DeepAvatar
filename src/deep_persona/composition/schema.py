"""Schemas for decoupled Scenarios and Relationships."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ScenarioDefinition(BaseModel):
    """Pure situational context independent of character personality core."""
    id: str
    title: str
    initial_context: str
    user_role: str
    persona_role: str
    location: Optional[str] = None
    constraints: List[str] = Field(default_factory=list)
    baseline_state_offset: Dict[str, float] = Field(default_factory=dict)


class RelationshipDefinition(BaseModel):
    """Interpersonal stance and history between a persona and a specific interlocutor."""
    id: str
    source_persona_id: str
    target_character: str
    relation: str  # e.g. "father", "classmate", "stranger", "superior"
    stance: str
    shared_history_summary: str = ""
    interaction_rules: List[str] = Field(default_factory=list)
    trust_bias: float = 0.0
    defensiveness_bias: float = 0.0
