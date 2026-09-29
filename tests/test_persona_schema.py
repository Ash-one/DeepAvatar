"""Tests for Persona schema and YAML loader."""

from pathlib import Path
import pytest
from deep_persona.persona.loader import load_persona
from deep_persona.persona.schema import PersonaConfig

PERSONAS_DIR = Path(__file__).resolve().parents[1] / "personas"


def test_load_evelyn():
    yaml_path = PERSONAS_DIR / "evelyn.yaml"
    persona, content_hash = load_persona(yaml_path)
    assert persona.persona.id == "evelyn"
    assert persona.persona.age == 16
    assert persona.scenario.user_role == "parent"
    assert len(persona.middle_layer.conditional_information) == 2
    assert len(persona.internal_layer.motivations) == 3
    assert len(content_hash) == 64  # SHA256 hex


def test_load_toy_persona():
    yaml_path = PERSONAS_DIR / "toy_persona.yaml"
    persona, content_hash = load_persona(yaml_path)
    assert persona.persona.id == "toy_persona"
    assert persona.persona.name == "Leo"
    assert persona.dynamics.initial_stage == "guarded"


def test_load_sarah():
    yaml_path = PERSONAS_DIR / "sarah.yaml"
    persona, _ = load_persona(yaml_path)
    assert persona.persona.id == "sarah"
    assert persona.scenario.user_role == "counselor"


def test_load_xianglin_sao_evidence_grounded():
    yaml_path = PERSONAS_DIR / "xianglin_sao.yaml"
    persona, _ = load_persona(yaml_path)
    assert persona.persona.id == "xianglin_sao"
    assert len(persona.evidence_index) == 4
    assert len(persona.internal_layer.latent_hypotheses) == 2
    assert persona.internal_layer.latent_hypotheses[0].confidence == 0.90
    assert len(persona.external_layer.behavior_patterns) == 2
    assert persona.external_layer.voice_profile is not None
    assert persona.dynamics.baseline is not None
    assert persona.dynamics.baseline.trust == 0.15



def test_evidence_grounded_schema_models():
    from deep_persona.persona.schema import (
        Evidence,
        EvidenceSource,
        EvidenceContext,
        EvidenceObservation,
        TraitHypothesis,
        BehaviorPattern,
        VoiceProfile,
        DynamicsBaseline,
        EventSensitivity,
    )

    ev = Evidence(
        id="ev_001",
        source=EvidenceSource(chapter=1, scene="Intro", span="She murmured."),
        type="dialogue",
        context=EvidenceContext(situation="confrontation", interlocutor="mother"),
        observation=EvidenceObservation(speech="I was there.", behavior="looking down"),
        confidence=0.92,
    )
    assert ev.id == "ev_001"
    assert ev.source.chapter == 1
    assert ev.context.interlocutor == "mother"

    hyp = TraitHypothesis(
        id="hyp_001",
        hypothesis="Needs peer validation",
        description="Driven by fear of exclusion",
        confidence=0.85,
        evidence_for=["ev_001"],
        evidence_against=[],
    )
    assert hyp.confidence == 0.85
    assert hyp.evidence_for == ["ev_001"]

    bp = BehaviorPattern(
        id="bp_001",
        trigger={"event": "criticism", "relationship": "parent"},
        appraisal=["feels_attacked"],
        response_tendencies={"withdrawal": 0.8, "deflection": 0.5},
        evidence=["ev_001"],
    )
    assert bp.response_tendencies["withdrawal"] == 0.8

    vp = VoiceProfile(
        lexical={"sentence_length": "short"},
        discourse={"preferred_patterns": ["ellipsis"]},
        pragmatic={"directness": 0.4},
        exemplars=[{"evidence_id": "ev_001", "quote": "I was there."}],
    )
    assert vp.pragmatic["directness"] == 0.4


def test_persona_config_with_evidence_and_dynamics():
    data = {
        "persona": {
            "id": "test_v2",
            "name": "Test V2",
            "age": 25,
            "role": "Analyst",
        },
        "scenario": {
            "title": "Briefing",
            "initial_context": "At the meeting room.",
            "user_role": "Director",
            "persona_role": "Analyst",
        },
        "external_layer": {
            "communication_style": ["precise"],
            "emotional_tone": ["calm"],
            "observable_behavior": ["taking notes"],
        },
        "middle_layer": {
            "beliefs": ["Data does not lie"],
        },
        "internal_layer": {
            "motivations": ["Pursuit of truth"],
            "fears": ["Inaccuracy"],
            "psychological_needs": ["Cognitive clarity"],
            "latent_hypotheses": [
                {
                    "id": "hyp_perfectionism",
                    "hypothesis": "Hyper-vigilant about precision",
                    "confidence": 0.9,
                    "evidence_for": ["ev_101"],
                }
            ],
        },
        "dynamics": {
            "baseline": {"trust": 0.4, "defensiveness": 0.5, "engagement": 0.7},
            "sensitivities": {
                "criticism": {"trust_delta": -0.1, "defensiveness_delta": 0.15, "engagement_delta": 0.0}
            },
        },
        "evidence_index": [
            {
                "id": "ev_101",
                "type": "behavior",
                "observation": {"behavior": "Double checked dataset 3 times."},
            }
        ],
    }

    cfg = PersonaConfig.model_validate(data)
    assert cfg.persona.id == "test_v2"
    assert len(cfg.evidence_index) == 1
    assert cfg.internal_layer.latent_hypotheses[0].id == "hyp_perfectionism"
    assert cfg.dynamics.baseline.trust == 0.4
    assert cfg.dynamics.sensitivities["criticism"].defensiveness_delta == 0.15

