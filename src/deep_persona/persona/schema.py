"""Pydantic schemas for Persona definition, supporting Evidence-Grounded construction and Authenticity Transformation."""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, model_validator
from deep_persona.memory.schema import MemoryConfig


# --- Evidence and Grounding Schemas ---

class EvidenceSource(BaseModel):
    chapter: Optional[Union[int, str]] = None
    scene: Optional[str] = None
    span: Optional[str] = None


class EvidenceContext(BaseModel):
    situation: Optional[str] = None
    interlocutor: Optional[str] = None


class EvidenceObservation(BaseModel):
    speech: Optional[str] = None
    behavior: Optional[str] = None
    content: Optional[str] = None


class Evidence(BaseModel):
    id: str
    source: EvidenceSource = Field(default_factory=EvidenceSource)
    type: str = "dialogue"  # dialogue, behavior, explicit_statement, narration
    context: EvidenceContext = Field(default_factory=EvidenceContext)
    observation: EvidenceObservation = Field(default_factory=EvidenceObservation)
    confidence: float = 1.0


class TraitHypothesis(BaseModel):
    id: str
    hypothesis: str
    description: str = ""
    confidence: float = 0.8
    evidence_for: List[str] = Field(default_factory=list)
    evidence_against: List[str] = Field(default_factory=list)


class BehaviorPattern(BaseModel):
    id: str
    trigger: Dict[str, Any] = Field(default_factory=dict)
    appraisal: List[str] = Field(default_factory=list)
    response_tendencies: Dict[str, float] = Field(default_factory=dict)
    evidence: List[str] = Field(default_factory=list)


class VoiceExemplar(BaseModel):
    quote: str
    context: Optional[str] = None
    interlocutor: Optional[str] = None
    emotional_tone: Optional[str] = None
    speech_act: Optional[str] = None
    speech_register: Optional[str] = Field(default=None, alias="register")


class VoiceProfile(BaseModel):
    lexical: Dict[str, Any] = Field(default_factory=dict)
    discourse: Dict[str, Any] = Field(default_factory=dict)
    pragmatic: Dict[str, Any] = Field(default_factory=dict)
    exemplars: List[Union[VoiceExemplar, Dict[str, Any]]] = Field(default_factory=list)


# --- Core Layer Schemas ---

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
    voice_profile: Optional[VoiceProfile] = None
    behavior_patterns: List[BehaviorPattern] = Field(default_factory=list)


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
    appraisal_patterns: List[str] = Field(default_factory=list)


class InternalLayer(BaseModel):
    motivations: List[str] = Field(default_factory=list)
    fears: List[str] = Field(default_factory=list)
    psychological_needs: List[str] = Field(default_factory=list)
    non_disclosure_rules: List[str] = Field(default_factory=list)
    latent_hypotheses: List[TraitHypothesis] = Field(default_factory=list)


# --- Dynamics & Embodied Expressions ---

class StageConfig(BaseModel):
    description: str


class TransitionRule(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_stage: str = Field(alias="from")
    to_stage: str = Field(alias="to")
    trigger: str


class DynamicsBaseline(BaseModel):
    trust: float = 0.20
    defensiveness: float = 0.80
    engagement: float = 0.40


class EventSensitivity(BaseModel):
    trust_delta: float = 0.0
    defensiveness_delta: float = 0.0
    engagement_delta: float = 0.0


class DynamicsConfig(BaseModel):
    initial_stage: str = "guarded"
    stages: Dict[str, StageConfig] = Field(default_factory=dict)
    transitions: List[TransitionRule] = Field(default_factory=list)
    baseline: Optional[DynamicsBaseline] = None
    sensitivities: Dict[str, EventSensitivity] = Field(default_factory=dict)
    recovery: Dict[str, float] = Field(default_factory=dict)


class EmbodiedExpressionConfig(BaseModel):
    enabled: bool = False
    format: str = "[action]"
    allowed: List[str] = Field(default_factory=list)


class PersonaConfig(BaseModel):
    persona: PersonaIdentity
    scenario: Optional[ScenarioConfig] = None
    external_layer: ExternalLayer
    middle_layer: MiddleLayer
    internal_layer: InternalLayer
    dynamics: DynamicsConfig = Field(default_factory=DynamicsConfig)
    embodied_expression: EmbodiedExpressionConfig = Field(default_factory=EmbodiedExpressionConfig)
    constraints: List[str] = Field(default_factory=list)
    evidence_index: List[Evidence] = Field(default_factory=list)
    temporal_context: Optional[Dict[str, Any]] = None
    memory: Optional[MemoryConfig] = None

    @model_validator(mode="before")
    @classmethod
    def _normalize_persona_identity(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "persona" not in data and ("id" in data or "name" in data):
                data = dict(data)
                data["persona"] = {
                    "id": data.get("id", "character"),
                    "name": data.get("name", "Character"),
                    "age": data.get("age", 30),
                    "role": data.get("role", "character"),
                }
        return data
