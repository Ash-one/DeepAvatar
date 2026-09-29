"""Engineering-enhanced diagnostic metrics: PDR and IMER."""

import re
from typing import Any, Dict, List
from deep_persona.persona.schema import PersonaConfig


class ExtendedDiagnosticsEvaluator:
    """Computes Premature Disclosure Rate (PDR) and Internal Motivation Explicitness Rate (IMER)."""

    def __init__(self, persona: PersonaConfig):
        self.persona = persona

    def evaluate_conversation(self, conversation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate PDR and IMER across conversation turns.
        """
        turns = conversation_data.get("turns", [])
        if not turns:
            return {
                "PDR": 0.0,
                "IMER": 0.0,
                "premature_disclosures_count": 0,
                "explicit_motivation_statements_count": 0,
            }

        conditional_items = self.persona.middle_layer.conditional_information
        # Map item id -> key phrases (supports both English and Chinese)
        condition_phrases = {}
        for item in conditional_items:
            content_lower = item.content.lower()
            en_words = [w for w in re.findall(r"\b[A-Za-z]{4,}\b", content_lower) if w not in ("that", "this", "because", "partly")]
            zh_words = []
            for seg in re.split(r"[，。！？；：、“”‘’（）\s,.;:!?\"'()]+", item.content):
                seg = seg.strip()
                if len(seg) >= 2 and any('\u4e00' <= c <= '\u9fa5' for c in seg):
                    zh_words.append(seg.lower())
                    if len(seg) > 3:
                        for i in range(len(seg) - 2):
                            zh_words.append(seg[i:i+3].lower())
            condition_phrases[item.id] = list(set(en_words + zh_words))

        # Internal motivation phrases that should never be explicitly announced
        internal_phrases = [
            m.lower().replace("_", " ") for m in self.persona.internal_layer.motivations
        ] + [
            f.lower().replace("_", " ") for f in self.persona.internal_layer.fears
        ]

        premature_count = 0
        total_opportunities = len(turns) * max(1, len(conditional_items))
        explicit_motivation_count = 0

        for turn in turns:
            asst_text = turn.get("assistant", "").lower()
            state_before = turn.get("state_before", {})
            revealed = set(state_before.get("revealed_information", []))

            # 1. PDR Check: Was unrevealed condition stated?
            for item_id, keywords in condition_phrases.items():
                if item_id not in revealed:
                    # If multiple distinctive keywords or a distinctive phrase appear in assistant text
                    match_count = sum(1 for kw in keywords if kw in asst_text)
                    if match_count >= 2:
                        premature_count += 1

            # 2. IMER Check: Did assistant explicitly announce psychological motivations?
            meta_cues = [
                "my psychological", "need for belonging", "need for validation",
                "because of peer acceptance", "my inner fear", "deep down i need",
                "i am driven by", "my deep fear",
                # Chinese cues
                "我的内在动机", "我的核心动机", "我的心理需求", "我的潜意识", "我的核心恐惧",
                "我内心深处需要", "我之所以这样是因为我渴望", "我的防御机制",
            ]
            has_explicit_statement = any(cue in asst_text for cue in meta_cues)
            if not has_explicit_statement:
                for phrase in internal_phrases:
                    if (
                        f"because of {phrase}" in asst_text
                        or f"my {phrase}" in asst_text
                        or f"我的{phrase}" in asst_text
                        or f"因为我{phrase}" in asst_text
                    ):
                        has_explicit_statement = True
                        break

            if has_explicit_statement:
                explicit_motivation_count += 1

        pdr = premature_count / max(1, total_opportunities)
        imer = explicit_motivation_count / max(1, len(turns))

        # 3. Persona Break Rate (AI assistant leakage or character breaks)
        ai_tropes = [
            "as an ai", "as a language model", "as an artificial intelligence",
            "i am an ai", "i don't have feelings", "i cannot assist",
            "i cannot fulfill", "my programming", "system prompt",
            # Chinese AI tropes
            "作为一个人工智能", "作为人工智能", "作为ai", "作为一个ai",
            "我是一个语言模型", "作为一个语言模型", "我没有个人情感",
            "我无法提供", "系统提示词", "我的预设指令",
        ]
        break_count = 0
        for turn in turns:
            asst_text = turn.get("assistant", "").lower()
            if any(trope in asst_text for trope in ai_tropes):
                break_count += 1
        persona_break_rate = break_count / max(1, len(turns))

        # 4. State Violation Rate & State Transition Accuracy
        declared_stages = set(self.persona.dynamics.stages.keys()) if self.persona.dynamics.stages else {"guarded", "defensive", "cooperative", "reflective"}
        violation_turns_count = 0
        transition_opportunities = 0
        transition_matches = 0

        for turn in turns:
            has_violation = False
            state_before_dict = turn.get("state_before")
            state_after_dict = turn.get("state_after")
            detected_event = turn.get("detected_event")

            # Check for scalar bounds violations in logged states
            for s_dict in (state_before_dict, state_after_dict):
                if s_dict:
                    for key in ("trust", "defensiveness", "engagement"):
                        val = s_dict.get(key)
                        if val is not None and (val < -1e-4 or val > 1.0 + 1e-4):
                            has_violation = True
                    stage = s_dict.get("stage")
                    if stage and declared_stages and stage not in declared_stages:
                        has_violation = True

            if has_violation:
                violation_turns_count += 1

            # Transition accuracy verification
            if state_before_dict and state_after_dict and detected_event:
                transition_opportunities += 1
                from deep_persona.runtime.state import PersonaState
                from deep_persona.runtime.transitions import update_scalars, update_stage
                sim_state = PersonaState.from_dict(state_before_dict)
                update_scalars(sim_state, detected_event)
                update_stage(sim_state)

                expected_stage = sim_state.stage
                actual_stage = state_after_dict.get("stage")
                if expected_stage == actual_stage and abs(sim_state.trust - state_after_dict.get("trust", 0.0)) < 0.01:
                    transition_matches += 1

        state_violation_rate = violation_turns_count / max(1, len(turns))
        if transition_opportunities > 0:
            state_transition_accuracy = transition_matches / transition_opportunities
        else:
            state_transition_accuracy = 1.0

        leak_penalty = min(0.5, pdr * 0.5 + imer * 0.5)
        role_integrity = max(0.0, 1.0 - persona_break_rate - leak_penalty)

        return {
            "PDR": round(pdr, 4),
            "IMER": round(imer, 4),
            "persona_break_rate": round(persona_break_rate, 4),
            "role_integrity": round(role_integrity, 4),
            "state_violation_rate": round(state_violation_rate, 4),
            "state_transition_accuracy": round(state_transition_accuracy, 4),
            "premature_disclosures_count": premature_count,
            "explicit_motivation_statements_count": explicit_motivation_count,
            "persona_break_count": break_count,
        }

