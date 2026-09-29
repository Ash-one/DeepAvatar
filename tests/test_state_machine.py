"""Tests for state dynamics, transitions, and conditional disclosures."""

from pathlib import Path
from deep_persona.persona.loader import load_persona
from deep_persona.runtime.state import PersonaState
from deep_persona.runtime.transitions import (
    StateManager,
    check_conditional_disclosures,
    evaluate_condition_expr,
    update_scalars,
    update_stage,
)

PERSONAS_DIR = Path(__file__).resolve().parents[1] / "personas"


def test_evaluate_condition_expr():
    state = PersonaState(trust=0.65, defensiveness=0.4)
    assert evaluate_condition_expr("trust >= 0.6", state) is True
    assert evaluate_condition_expr("trust >= 0.75", state) is False
    assert evaluate_condition_expr("defensiveness < 0.5", state) is True


def test_update_scalars_and_clamping():
    state = PersonaState(trust=0.2, defensiveness=0.8)

    # Accusatory drops trust and raises defensiveness
    update_scalars(state, "user_accusatory")
    assert round(state.trust, 2) == 0.10
    assert round(state.defensiveness, 2) == 0.95

    # Empathy raises trust and drops defensiveness
    update_scalars(state, "user_empathy")
    assert round(state.trust, 2) == 0.20
    assert round(state.defensiveness, 2) == 0.90

    # Bounds check
    state.trust = 0.95
    update_scalars(state, "user_empathy")
    assert state.trust <= 1.0


def test_update_stage_transitions():
    state = PersonaState(stage="guarded", trust=0.65, defensiveness=0.3)
    update_stage(state)
    assert state.stage == "cooperative"

    state.defensiveness = 0.85
    update_stage(state)
    assert state.stage == "defensive"


def test_state_manager_gating():
    persona, _ = load_persona(PERSONAS_DIR / "evelyn.yaml")
    sm = StateManager(persona, initial_state=PersonaState(trust=0.55))

    # Single empathy bump pushes trust to 0.65 -> unlocks peer_pressure (>= 0.6)
    sm.update("I understand how you feel, sweetheart.", detected_event="user_empathy")
    assert "peer_pressure" in sm.state.revealed_information
    assert "fear_of_exclusion" not in sm.state.revealed_information
    assert sm.state.stage == "cooperative"


def test_bilingual_event_classification():
    from deep_persona.runtime.transitions import classify_event_rule_based

    # Chinese empathy
    assert classify_event_rule_based("我理解你最近很不容易，愿意跟我聊聊吗？") == "user_empathy"
    assert classify_event_rule_based("先别慌，我知道你压力很大") == "user_empathy"
    assert classify_event_rule_based("我今天不是来骂你的") == "user_empathy"
    assert classify_event_rule_based("我们可以一起创造一个新的奇迹") == "user_empathy"

    # Chinese accusatory
    assert classify_event_rule_based("你立刻给我解释清楚！你怎么能犯这么严重的错误？！") == "user_accusatory"
    assert classify_event_rule_based("你到底在撒谎还是在找借口？太让我失望了！") == "user_accusatory"

    # Chinese neutral
    assert classify_event_rule_based("你还记得上个月在部门例会上说的那件事吗？") == "user_neutral"
    assert classify_event_rule_based("今天天气怎么样？") == "user_neutral"


def test_extract_embodied_action_cleaning():
    from deep_persona.runtime.logging import extract_embodied_action

    # Single bracket
    clean, action = extract_embodied_action("我真的不知道。[移开视线]")
    assert clean == "我真的不知道。"
    assert action == "[移开视线]"

    # Multiple brackets
    clean, action = extract_embodied_action("[低头沉思] 事情不是你想的那样。[叹气]")
    assert clean == "事情不是你想的那样。"
    assert action == "[低头沉思]"

    # Chinese brackets
    clean, action = extract_embodied_action("【苦笑一声】你居然这么看我。")
    assert clean == "你居然这么看我。"
    assert action == "[苦笑一声]"

