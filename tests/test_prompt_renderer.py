"""Tests for PromptRenderer and information gating."""

from pathlib import Path
from deep_persona.persona.loader import load_persona
from deep_persona.persona.renderer import PromptRenderer
from deep_persona.runtime.state import PersonaState

PERSONAS_DIR = Path(__file__).resolve().parents[1] / "personas"


def test_render_flat():
    persona, _ = load_persona(PERSONAS_DIR / "evelyn.yaml")
    renderer = PromptRenderer()
    prompt = renderer.render_persona(persona, mode="flat")
    assert "You are Evelyn" in prompt
    assert "# EXTERNAL LAYER" not in prompt  # Flat should not have layer headers
    assert "Remain in character" in prompt


def test_render_deep_faithful():
    persona, _ = load_persona(PERSONAS_DIR / "evelyn.yaml")
    renderer = PromptRenderer()
    prompt = renderer.render_persona(persona, mode="deep")
    assert "# ROLE" in prompt
    assert "# EXTERNAL LAYER" in prompt
    assert "# MIDDLE LAYER" in prompt
    assert "# INTERNAL LAYER" in prompt
    assert "peer_pressure" in prompt


def test_render_external_state_information_gating():
    persona, _ = load_persona(PERSONAS_DIR / "evelyn.yaml")
    renderer = PromptRenderer()

    # Initial state (nothing revealed)
    state = PersonaState(stage="guarded", trust=0.2)
    prompt_initial = renderer.render_persona(persona, mode="deep_external_state", state=state)
    assert "No conditional information has been unlocked yet" in prompt_initial
    assert "you began vaping partly because of peer pressure" not in prompt_initial

    # State with peer_pressure unlocked
    state.revealed_information.add("peer_pressure")
    prompt_unlocked = renderer.render_persona(persona, mode="deep_external_state", state=state)
    assert "peer_pressure" in prompt_unlocked
    assert "you began vaping partly because of peer pressure" in prompt_unlocked
    # fear_of_exclusion still not unlocked
    assert "fear_of_exclusion" not in prompt_unlocked
