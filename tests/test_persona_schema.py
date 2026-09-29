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
