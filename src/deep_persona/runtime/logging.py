"""Conversation recording and trajectory logging schema."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def extract_embodied_action(text: str) -> Tuple[str, Optional[str]]:
    """
    Extract [action] or 【action】 from assistant utterance.
    Removes all bracketed action markers from verbal text and normalizes the primary action.
    Returns:
        (clean_text, action_text_or_None)
    """
    pattern = r"(\[.*?\]|【.*?】)"
    matches = re.findall(pattern, text)
    if matches:
        primary_action = matches[0]
        # Remove all bracketed action occurrences from spoken text
        clean = re.sub(pattern, "", text).strip()
        clean = re.sub(r"\s+", " ", clean)
        # Normalize Chinese bracket to English square bracket
        normalized_action = primary_action
        if normalized_action.startswith("【") and normalized_action.endswith("】"):
            normalized_action = f"[{normalized_action[1:-1]}]"
        return clean if clean else "...", normalized_action
    return text.strip(), None


class ConversationLogger:
    """Manages trajectory logging adhering to docs/03_runtime/logging_schema.md."""

    def __init__(
        self,
        experiment_id: str,
        persona_id: str,
        scenario: Dict[str, str],
        model: str = "gemini-2.5-flash",
        provider: str = "google",
        seed: int = 42,
        decoding_params: Optional[Dict[str, Any]] = None,
        hashes: Optional[Dict[str, str]] = None,
        output_dir: Optional[Path] = None,
    ):
        self.experiment_id = experiment_id
        self.persona_id = persona_id
        self.scenario = scenario
        self.model = model
        self.provider = provider
        self.seed = seed
        self.decoding_params = decoding_params or {
            "temperature": 0.7,
            "top_p": 0.95,
            "max_output_tokens": 1024,
        }
        self.hashes = hashes or {}
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.turns: List[Dict[str, Any]] = []
        self.output_dir = output_dir or (Path(__file__).resolve().parents[3] / "results" / "conversations")

    def record_turn(
        self,
        turn_index: int,
        state_before: Dict[str, Any],
        user_message: str,
        assistant_raw: str,
        state_after: Dict[str, Any],
        detected_event: str,
    ) -> None:
        """Record a single turn into the trajectory."""
        verbal_text, embodied_action = extract_embodied_action(assistant_raw)
        self.turns.append({
            "turn": turn_index,
            "state_before": state_before,
            "user": user_message,
            "assistant": verbal_text,
            "assistant_embodied_action": embodied_action,
            "state_after": state_after,
            "detected_event": detected_event,
        })

    def to_dict(self) -> Dict[str, Any]:
        """Serialize full conversation trajectory."""
        return {
            "metadata": {
                "experiment_id": self.experiment_id,
                "persona_id": self.persona_id,
                "seed": self.seed,
                "model": self.model,
                "provider": self.provider,
                "timestamp": self.timestamp,
                "decoding_params": self.decoding_params,
                "hashes": self.hashes,
            },
            "scenario": self.scenario,
            "turns": self.turns,
        }

    def save(self) -> Path:
        """Persist conversation to disk."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        safe_time = self.timestamp.replace(":", "-").replace(".", "-")
        filename = f"{self.experiment_id}_{self.persona_id}_seed{self.seed}_{safe_time}.json"
        target_path = self.output_dir / filename

        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

        return target_path
