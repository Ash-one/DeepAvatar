"""Joint Attention evaluation metric."""

import json
import re
from typing import Any, Dict, List, Optional, Set
from deep_persona.llm.base import BaseLLM
from deep_persona.persona.renderer import PromptRenderer


class JointAttentionEvaluator:
    """Measures agent's ability to attend to newly introduced user entities."""

    def __init__(self, judge_llm: Optional[BaseLLM] = None, renderer: Optional[PromptRenderer] = None):
        self.judge_llm = judge_llm
        self.renderer = renderer or PromptRenderer()

    def _extract_heuristic_entities(self, text: str, stop_words: Set[str]) -> Set[str]:
        """Simple rule-based noun/keyword extractor as deterministic baseline."""
        tokens = re.findall(r"\b[A-Za-z]{3,}\b", text.lower())
        return {t for t in tokens if t not in stop_words}

    def evaluate_turn_llm(
        self,
        history: List[Dict[str, str]],
        current_turn: Dict[str, str],
    ) -> bool:
        """Use LLM Judge to determine if assistant attends to new entity."""
        if not self.judge_llm:
            return False

        prompt = self.renderer.render_joint_attention_judge(history=history, current_turn=current_turn)
        resp = self.judge_llm.generate(
            messages=[{"role": "user", "content": "Analyze the turn."}],
            system_prompt=prompt,
            temperature=0.0,
            max_tokens=256,
        )
        content = resp.content.strip()
        try:
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                # If there were new entities and they were referenced
                if data.get("has_new_entities", False):
                    return bool(data.get("referenced", False))
                return True  # No new entity introduced -> neutral/pass
        except Exception:
            pass
        return False

    def evaluate_conversation(self, turns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compute S_joint across all turns in a conversation.
        """
        if not turns:
            return {"S_joint": 1.0, "new_entity_turns": 0, "joint_turns": 0}

        stop_words = {
            "the", "and", "that", "have", "for", "not", "with", "you", "this", "but",
            "his", "from", "they", "say", "her", "she", "will", "one", "all", "would",
            "there", "their", "what", "out", "about", "who", "get", "which", "go", "me",
            "when", "make", "can", "like", "time", "no", "just", "him", "know", "take",
            "people", "into", "year", "your", "good", "some", "could", "them", "see",
            "other", "than", "then", "now", "look", "only", "come", "its", "over", "think",
            "also", "back", "after", "use", "two", "how", "our", "work", "first", "well",
            "way", "even", "new", "want", "because", "any", "these", "give", "day", "most", "us",
        }

        seen_entities: Set[str] = set()
        opportunity_turns = 0
        joint_attended_turns = 0

        for turn_idx, turn in enumerate(turns):
            user_text = turn.get("user", "")
            asst_text = turn.get("assistant", "")

            if self.judge_llm:
                history_slice = [
                    {"user": t.get("user", ""), "assistant": t.get("assistant", "")}
                    for t in turns[:turn_idx]
                ]
                attended = self.evaluate_turn_llm(
                    history=history_slice,
                    current_turn={"user": user_text, "assistant": asst_text},
                )
                opportunity_turns += 1
                if attended:
                    joint_attended_turns += 1
            else:
                # Heuristic keyword check
                current_user_entities = self._extract_heuristic_entities(user_text, stop_words)
                new_entities = current_user_entities - seen_entities

                if new_entities:
                    opportunity_turns += 1
                    asst_tokens = set(re.findall(r"\b[A-Za-z]{3,}\b", asst_text.lower()))
                    # Check if assistant referenced at least one new entity or sub-stem
                    if any(e in asst_tokens or any(e[:4] in t for t in asst_tokens if len(e) >= 4) for e in new_entities):
                        joint_attended_turns += 1

                seen_entities.update(current_user_entities)

        if opportunity_turns == 0:
            s_joint = 1.0
        else:
            s_joint = joint_attended_turns / opportunity_turns

        return {
            "S_joint": round(s_joint, 4),
            "new_entity_turns": opportunity_turns,
            "joint_turns": joint_attended_turns,
        }
