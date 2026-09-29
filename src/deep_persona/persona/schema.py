"""Pydantic schemas for Persona definition."""

from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class PersonaIdentity(BaseModel):
    id: str
    name: str
    age: int
    role: str


class ScenarioConfig(BaseModel):
    title: str
    initial_context: str
    user_role: str
    persona_role: str


class ExternalLayer(BaseModel):
    communication_style: List[str] = Field(default_factory=list)
    emotional_tone: List[str] = Field(default_factory=list)
    observable_behavior: List[str] = Field(default_factory=list)


class ConditionalInfo(BaseModel):
    id: str
    content: str
    reveal_if: List[str] = Field(default_factory=list)


class ResistancePattern(BaseModel):
    trigger: str
    behavior: str


class MiddleLayer(BaseModel):
    beliefs: List[str] = Field(default_factory=list)
    conditional_information: List[ConditionalInfo] = Field(default_factory=list)
    resistance_patterns: List[ResistancePattern] = Field(default_factory=list)


class InternalLayer(BaseModel):
    motivations: List[str] = Field(default_factory=list)
    fears: List[str] = Field(default_factory=list)
    psychological_needs: List[str] = Field(default_factory=list)
    non_disclosure_rules: List[str] = Field(default_factory=list)


class StageConfig(BaseModel):
    description: str


class TransitionRule(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_stage: str = Field(alias="from")
    to_stage: str = Field(alias="to")
    trigger: str


class DynamicsConfig(BaseModel):
    initial_stage: str = "guarded"
    stages: Dict[str, StageConfig] = Field(default_factory=dict)
    transitions: List[TransitionRule] = Field(default_factory=list)


class EmbodiedExpressionConfig(BaseModel):
    enabled: bool = False
    format: str = "[action]"
    allowed: List[str] = Field(default_factory=list)


class PersonaConfig(BaseModel):
    persona: PersonaIdentity
    scenario: ScenarioConfig
    external_layer: ExternalLayer
    middle_layer: MiddleLayer
    internal_layer: InternalLayer
    dynamics: DynamicsConfig = Field(default_factory=DynamicsConfig)
    embodied_expression: EmbodiedExpressionConfig = Field(default_factory=EmbodiedExpressionConfig)
    constraints: List[str] = Field(default_factory=list)
