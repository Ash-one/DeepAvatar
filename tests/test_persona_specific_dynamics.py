"""Tests for Phase B: Persona-Specific Psychological Dynamics."""

from pathlib import Path
import pytest

from deep_persona.llm.base import BaseLLM, LLMResponse
from deep_persona.persona.loader import load_persona
from deep_persona.persona.renderer import PromptRenderer
from deep_persona.persona.schema import (
    DynamicsBaseline,
    DynamicsConfig,
    EventSensitivity,
    ExternalLayer,
    InternalLayer,
    MiddleLayer,
    PersonaConfig,
    PersonaIdentity,
    ScenarioConfig,
    TransitionRule,
)
from deep_persona.runtime.agent import PersonaAgent
from deep_persona.runtime.state import PersonaState
from deep_persona.runtime.transitions import (
    StateManager,
    classify_event_rule_based,
    update_scalars,
    update_stage,
)

PERSONAS_DIR = Path(__file__).resolve().parents[1] / "personas"


def test_baseline_initialization():
    # 1. Persona with explicit baseline (xianglin_sao)
    xianglin, _ = load_persona(PERSONAS_DIR / "xianglin_sao.yaml")
    state_xl = PersonaState.create_for_persona(xianglin)
    assert state_xl.trust == 0.15
    assert state_xl.defensiveness == 0.85
    assert state_xl.engagement == 0.50

    # 2. Legacy persona without explicit baseline (evelyn)
    evelyn, _ = load_persona(PERSONAS_DIR / "evelyn.yaml")
    state_ev = PersonaState.create_for_persona(evelyn)
    assert state_ev.trust == 0.20
    assert state_ev.defensiveness == 0.80
    assert state_ev.engagement == 0.40


def test_persona_specific_sensitivities():
    xianglin, _ = load_persona(PERSONAS_DIR / "xianglin_sao.yaml")
    state_xl = PersonaState.create_for_persona(xianglin)
    initial_trust = state_xl.trust
    initial_def = state_xl.defensiveness

    # Xianglin Sao sensitivity on criticism: trust -0.20, def +0.25, eng -0.10
    update_scalars(state_xl, event="user_accusatory", persona=xianglin)
    assert state_xl.trust == max(0.0, initial_trust - 0.20)
    assert state_xl.defensiveness == min(1.0, initial_def + 0.25)
    assert state_xl.engagement == 0.50 - 0.10

    # Test empathy event
    state_xl2 = PersonaState.create_for_persona(xianglin)
    # empathy sensitivity: trust +0.15, def -0.10, eng +0.15
    update_scalars(state_xl2, event="user_empathy", persona=xianglin)
    assert state_xl2.trust == round(0.15 + 0.15, 2)
    assert state_xl2.defensiveness == round(0.85 - 0.10, 2)
    assert state_xl2.engagement == round(0.50 + 0.15, 2)


def test_recovery_decay_towards_character_baseline():
    xianglin, _ = load_persona(PERSONAS_DIR / "xianglin_sao.yaml")
    state = PersonaState.create_for_persona(xianglin)

    # Disturb state away from baseline (baseline: trust=0.15, def=0.85)
    state.trust = 0.05       # below baseline
    state.defensiveness = 0.95  # above baseline
    state.engagement = 0.70     # above baseline (0.50)

    # Neutral turn recovery:
    # trust_decay=0.01 -> 0.05 + 0.01 = 0.06
    # defensiveness_decay=0.02 -> 0.95 - 0.02 = 0.93
    update_scalars(state, event="user_neutral", persona=xianglin)
    assert round(state.trust, 4) == 0.06
    assert round(state.defensiveness, 4) == 0.93
    assert round(state.engagement, 4) == 0.69

    # Multiple neutral turns should converge to baseline
    for _ in range(50):
        update_scalars(state, event="user_neutral", persona=xianglin)

    assert round(state.trust, 2) == 0.15
    assert round(state.defensiveness, 2) == 0.85
    assert round(state.engagement, 2) == 0.50


def test_declarative_stage_transitions():
    cfg = PersonaConfig(
        persona=PersonaIdentity(id="custom", name="Custom", age=30, role="Tester"),
        scenario=ScenarioConfig(title="Test", initial_context="Ctx", user_role="User", persona_role="Persona"),
        external_layer=ExternalLayer(),
        middle_layer=MiddleLayer(),
        internal_layer=InternalLayer(),
        dynamics=DynamicsConfig(
            initial_stage="guarded",
            stages={
                "guarded": {"description": "guarded"},
                "open": {"description": "open"},
                "withdrawn": {"description": "withdrawn"},
            },
            transitions=[
                TransitionRule(from_stage="guarded", to_stage="open", trigger="trust >= 0.5"),
                TransitionRule(from_stage="open", to_stage="withdrawn", trigger="user_accusatory"),
            ],
            baseline=DynamicsBaseline(trust=0.3, defensiveness=0.6, engagement=0.5),
        ),
    )

    state = PersonaState.create_for_persona(cfg)
    assert state.stage == "guarded"

    # Evaluate with trust < 0.5 -> stays guarded
    update_stage(state, event="user_neutral", persona=cfg)
    assert state.stage == "guarded"

    # Raise trust >= 0.5 -> transitions to open
    state.trust = 0.6
    update_stage(state, event="user_neutral", persona=cfg)
    assert state.stage == "open"

    # Accusation -> transitions to withdrawn
    update_stage(state, event="user_accusatory", persona=cfg)
    assert state.stage == "withdrawn"


def test_state_manager_persona_specific_lifecycle():
    xianglin, _ = load_persona(PERSONAS_DIR / "xianglin_sao.yaml")
    sm = StateManager(xianglin)

    # Initialized from baseline
    assert sm.state.trust == 0.15
    assert sm.state.defensiveness == 0.85

    # Accusation turn
    st1 = sm.update("你在撒谎！立刻把事情解释清楚！")
    assert st1.defensiveness == 1.0  # 0.85 + 0.25 clamped
    assert st1.trust == 0.0          # 0.15 - 0.20 clamped
    assert st1.stage == "defensive"

    # Empathy turns
    sm.update("别害怕，我理解你的难处，坐下慢慢说。")
    assert sm.state.trust == 0.15


class MockDialogueLLM(BaseLLM):
    def generate(self, messages, system_prompt=None, **kwargs) -> LLMResponse:
        assert "# ROLE" in system_prompt
        assert "Behavior Patterns" in system_prompt or "Xianglin" in system_prompt or "祥林嫂" in system_prompt
        return LLMResponse(content="[微微颤抖] 我真傻，真的……", model="mock")


def test_persona_agent_with_phase_b_dynamics():
    xianglin, _ = load_persona(PERSONAS_DIR / "xianglin_sao.yaml")
    agent = PersonaAgent(
        persona=xianglin,
        mode="deep_external_state",
        llm=MockDialogueLLM(),
    )

    # Verify agent initialized with character-specific baseline
    assert agent.current_state.trust == 0.15
    assert agent.current_state.defensiveness == 0.85

    reply, before, after, event = agent.respond("我理解你的不容易，阿毛的事情谁也不想的。")
    assert event == "user_empathy"
    assert after.trust > before.trust
    assert after.defensiveness < before.defensiveness
    assert "[微微颤抖]" in reply


def test_prompt_rendering_with_behavior_patterns_and_exemplars():
    xianglin, _ = load_persona(PERSONAS_DIR / "xianglin_sao.yaml")
    renderer = PromptRenderer()
    state = PersonaState.create_for_persona(xianglin)

    rendered = renderer.render_persona(persona=xianglin, mode="deep_external_state", state=state)
    # Check Behavior Patterns rendered
    assert "Behavior Patterns" in rendered
    assert "bp_soul_inquiry" in rendered or "fearing_hell_punishment" in rendered
    # Check Voice Exemplars rendered
    assert "Authentic Voice Exemplars" in rendered
    assert "人死了之后，究竟有没有灵魂的？" in rendered
    # Check Latent Hypotheses rendered
    assert "Unconscious Latent Hypotheses" in rendered
    assert "hyp_existential_terror" in rendered or "对死后地狱酷刑" in rendered
