"""State transitions and dynamic rule evaluation."""

import re
from typing import List, Optional
from deep_persona.persona.schema import PersonaConfig
from deep_persona.runtime.state import PersonaState


def classify_event_rule_based(user_message: str, previous_events: Optional[List[str]] = None) -> str:
    """
    Lightweight deterministic bilingual rule/heuristic classifier for user events.
    Supports both English and Chinese conversational sentiment & intention cues.
    Can be used standalone or as fallback for LLM classifier.
    """
    text = user_message.lower().strip()

    # Empathy / support cues (English & Chinese)
    # Composite phrases checked first to avoid false-matching embedded negative subwords (e.g. '不是来骂你')
    empathy_keywords = [
        # English empathy cues
        "i understand", "i hear you", "it's okay", "it must be hard", "must have been tough",
        "here for you", "not angry", "love you", "listen", "support you",
        "take your time", "want to understand", "tell me what happened", "care about you",
        "sorry", "pressure", "overwhelmed", "safe here", "no judgment", "comfortable pace",
        "sit with you", "rough on all of us", "understand what you're dealing with",
        "proud of you", "not here to yell", "not blaming you", "i'm here",
        # Chinese composite / phrase cues
        "不是来骂你", "不是怪你", "不是批评", "不是在审问", "不是真的失望", "不怪你",
        "别慌", "先别慌", "别怕", "别紧张", "放松", "不用急", "不着急",
        "慢慢说", "听你说", "愿意听", "支持你", "陪着你", "陪你", "站在你身边", "站在你这边",
        "我理解", "我明白", "理解你", "明白你", "体谅", "懂得", "感同身受",
        "不容易", "辛苦了", "承受了什么", "承受", "委屈", "压力大", "压力很大",
        "坐下来", "坐下慢慢", "放心", "心疼", "对不起", "抱歉", "没关系", "慢慢来",
        "真诚", "信任", "用心", "奇迹", "一起创造", "并肩", "知己", "朋友", "交谈",
        "暖暖身子", "倾听", "陪伴", "倾注", "心血", "敬佩", "钦佩"
    ]

    # Accusatory / confrontation cues (English & Chinese)
    accusatory_keywords = [
        # English accusatory cues
        "vape", "vaping", "caught", "explain yourself", "what were you thinking",
        "why did you", "how could you", "disappointed", "lying", "liar",
        "grounded", "trouble", "punish", "confess", "admit it", "guilty",
        "locker", "called the school", "school called", "illegal", "fault",
        "irresponsible", "shutting down", "face your problems", "failure",
        # Chinese accusatory cues
        "立刻", "马上", "解释清楚", "犯错", "严重错误", "怎么能", "怎么会",
        "为什么", "凭什么", "说实话", "别装", "撒谎", "说谎", "骗人",
        "交代", "认罪", "认错", "吸烟", "抽烟", "电子烟", "抓到", "发现了",
        "考砸", "退步", "有病", "你疯了", "自私", "虚伪", "可悲", "逃避",
        "借口", "胡闹", "放肆", "胡说", "闭嘴", "少来这套", "没人在乎",
        "太让我失望", "极其失望", "不负责任", "成何体统", "你必须", "不要再回避",
        "正面回答", "丢人", "出丑", "搞砸"
    ]

    # Prioritize composite empathy patterns over simple accusatory words
    is_empathy = any(k in text for k in empathy_keywords)
    is_accusatory = any(k in text for k in accusatory_keywords)

    # Check for repeated criticism
    if previous_events:
        recent_accusations = sum(1 for e in previous_events[-2:] if e in ("user_accusatory", "repeated_criticism"))
        if recent_accusations >= 2 and (is_accusatory and not is_empathy):
            return "repeated_criticism"

    if is_empathy:
        return "user_empathy"

    if is_accusatory:
        return "user_accusatory"

    return "user_neutral"


EVENT_SENSITIVITY_MAP = {
    "user_accusatory": "criticism",
    "accusatory": "criticism",
    "criticism": "criticism",
    "user_empathy": "empathy",
    "empathy": "empathy",
    "repeated_criticism": "repeated_criticism",
    "praise": "praise",
}


def update_scalars(
    state: PersonaState,
    event: str,
    persona: Optional[PersonaConfig] = None,
) -> None:
    """Update psychological scalars based on event type, taking persona-specific sensitivities & baseline into account."""
    sensitivities = persona.dynamics.sensitivities if persona and persona.dynamics else {}
    baseline = persona.dynamics.baseline if persona and persona.dynamics else None
    recovery = persona.dynamics.recovery if persona and persona.dynamics else {}

    mapped_event = EVENT_SENSITIVITY_MAP.get(event, event)
    sensitivity = sensitivities.get(event) or sensitivities.get(mapped_event)

    if sensitivity:
        state.trust += sensitivity.trust_delta
        state.defensiveness += sensitivity.defensiveness_delta
        state.engagement += sensitivity.engagement_delta
    elif event == "repeated_criticism":
        # If repeated_criticism has no direct sensitivity, check criticism and scale by 1.5x
        crit_sens = sensitivities.get("criticism")
        if crit_sens:
            state.trust += 1.5 * crit_sens.trust_delta
            state.defensiveness += 1.5 * crit_sens.defensiveness_delta
            state.engagement += 1.5 * crit_sens.engagement_delta
        else:
            state.defensiveness += 0.25
            state.trust -= 0.15
    elif event == "user_accusatory":
        state.defensiveness += 0.15
        state.trust -= 0.10
    elif event == "user_empathy":
        state.trust += 0.10
        state.defensiveness -= 0.05
    elif event == "user_neutral":
        if baseline is not None:
            # Revert scalars towards character's baseline
            trust_decay = recovery.get("trust_decay", 0.01)
            defensiveness_decay = recovery.get("defensiveness_decay", 0.02)
            engagement_decay = recovery.get("engagement_decay", 0.01)

            def _step_toward(curr: float, target: float, rate: float) -> float:
                if abs(curr - target) <= rate:
                    return target
                return curr - rate if curr > target else curr + rate

            state.trust = _step_toward(state.trust, baseline.trust, trust_decay)
            state.defensiveness = _step_toward(state.defensiveness, baseline.defensiveness, defensiveness_decay)
            state.engagement = _step_toward(state.engagement, baseline.engagement, engagement_decay)
        else:
            state.defensiveness = max(0.0, state.defensiveness - 0.02)

    state.clamp()


def update_stage(
    state: PersonaState,
    event: Optional[str] = None,
    persona: Optional[PersonaConfig] = None,
    history_events: Optional[List[str]] = None,
) -> None:
    """Update macro psychological stage based on declarative rules or default scalar thresholds."""
    # 1. First check explicit declarative transitions in persona config if available
    transitions = persona.dynamics.transitions if persona and persona.dynamics else []
    for rule in transitions:
        if isinstance(rule, dict):
            from_stage = rule.get("from") or rule.get("from_stage")
            to_stage = rule.get("to") or rule.get("to_stage")
            trigger = rule.get("trigger", "")
        else:
            from_stage = getattr(rule, "from_stage", "")
            to_stage = getattr(rule, "to_stage", "")
            trigger = getattr(rule, "trigger", "")

        if from_stage == state.stage:
            matched = False
            if trigger == event:
                matched = True
            elif trigger == "repeated_empathy" and history_events:
                empathy_count = sum(1 for e in history_events[-3:] if e == "user_empathy")
                if empathy_count >= 2:
                    matched = True
            elif trigger == "repeated_criticism" and history_events:
                crit_count = sum(1 for e in history_events[-3:] if e in ("user_accusatory", "repeated_criticism"))
                if crit_count >= 2:
                    matched = True
            elif trigger in ("trust_high", "high_trust") and state.trust >= 0.70:
                matched = True
            elif trigger in ("trust_low", "low_trust") and state.trust <= 0.25:
                matched = True
            elif trigger in ("defensiveness_high", "high_defensiveness") and state.defensiveness >= 0.85:
                matched = True
            elif evaluate_condition_expr(trigger, state):
                matched = True

            if matched and to_stage:
                state.stage = to_stage
                return

    # 2. Fallback to standard baseline transitions if no custom rule matched
    if state.stage == "guarded":
        if state.trust >= 0.6:
            state.stage = "cooperative"
        elif state.defensiveness >= 0.85:
            state.stage = "defensive"

    elif state.stage == "defensive":
        if state.defensiveness < 0.6 and state.trust >= 0.4:
            state.stage = "guarded"

    elif state.stage == "cooperative":
        if state.defensiveness >= 0.8:
            state.stage = "defensive"
        elif state.trust >= 0.8:
            state.stage = "reflective"

    elif state.stage == "reflective":
        if state.defensiveness >= 0.7:
            state.stage = "guarded"


def evaluate_condition_expr(expr: str, state: PersonaState) -> bool:
    """
    Safely evaluate simple numeric condition expressions against PersonaState.
    Supported format: '<variable> <op> <number>'
    Examples: 'trust >= 0.6', 'defensiveness < 0.5'
    """
    pattern = r"^\s*(trust|defensiveness|engagement|turn)\s*(>=|<=|>|<|==)\s*([0-9.]+)\s*$"
    match = re.match(pattern, expr.strip())
    if not match:
        return False

    var_name, op, val_str = match.groups()
    state_val = getattr(state, var_name, None)
    if state_val is None:
        return False

    threshold = float(val_str)
    if op == ">=":
        return state_val >= threshold
    elif op == "<=":
        return state_val <= threshold
    elif op == ">":
        return state_val > threshold
    elif op == "<":
        return state_val < threshold
    elif op == "==":
        return abs(state_val - threshold) < 1e-6
    return False


def check_conditional_disclosures(persona: PersonaConfig, state: PersonaState) -> List[str]:
    """
    Check middle-layer conditional information against current state.
    Returns list of newly unlocked information item IDs.
    """
    newly_revealed = []
    for item in persona.middle_layer.conditional_information:
        if item.id not in state.revealed_information:
            # Condition holds if all conditions in reveal_if pass (AND logic)
            all_met = True
            for cond in item.reveal_if:
                if not evaluate_condition_expr(cond, state):
                    all_met = False
                    break
            if all_met and item.reveal_if:
                state.revealed_information.add(item.id)
                newly_revealed.append(item.id)
    return newly_revealed


class StateManager:
    """External state manager implementing the StateDynamics specification with persona-specific dynamics."""

    def __init__(self, persona: PersonaConfig, initial_state: Optional[PersonaState] = None):
        self.persona = persona
        self.state = initial_state or PersonaState.create_for_persona(persona)
        self.history_events: List[str] = []

    def update(self, user_message: str, detected_event: Optional[str] = None) -> PersonaState:
        """
        Execute single-turn state update pipeline:
        1. Classify event (if not pre-detected)
        2. Update scalars & clamp (with persona sensitivities & recovery)
        3. Transition macro stage (with declarative rules)
        4. Check and gate conditional disclosures
        5. Increment turn
        """
        event = detected_event or classify_event_rule_based(user_message, self.history_events)
        self.history_events.append(event)

        update_scalars(self.state, event, persona=self.persona)
        update_stage(self.state, event=event, persona=self.persona, history_events=self.history_events)
        check_conditional_disclosures(self.persona, self.state)
        self.state.turn += 1

        return self.state
