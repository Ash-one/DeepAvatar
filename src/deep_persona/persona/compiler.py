"""Persona Compiler: Induces a grounded 3-Layer Persona from structured atomic evidence."""

import json
import re
from typing import Any, Dict, List, Optional

from deep_persona.llm.base import BaseLLM
from deep_persona.llm.gemini import GeminiLLM
from deep_persona.persona.schema import (
    BehaviorPattern,
    ConditionalInfo,
    DynamicsBaseline,
    DynamicsConfig,
    EventSensitivity,
    Evidence,
    ExternalLayer,
    InternalLayer,
    MiddleLayer,
    PersonaConfig,
    PersonaIdentity,
    ResistancePattern,
    ScenarioConfig,
    StageConfig,
    TraitHypothesis,
    TransitionRule,
    VoiceProfile,
)

PERSONA_COMPILER_SYSTEM_PROMPT = """You are a computational psychologist and persona compiler.
Your task is to synthesize a structured 3-Layer Deep Persona from an authoritative list of ATOMIC EVIDENCE items.

CORE PRINCIPLE:
Every high-level persona inference must be grounded in the provided Evidence IDs!
- Every latent hypothesis in the internal layer MUST specify `evidence_for` referencing actual evidence IDs, and any counter-evidence `evidence_against`.
- Every situation-conditioned behavior pattern MUST cite supporting evidence IDs.
- Authentic voice exemplars MUST link directly to dialogue evidence IDs.

You must output strictly a valid JSON object matching the following structure:
```json
{
  "id": "lowercase_english_id (e.g. xianglin_sao, hamlet)",
  "name": "Character Name",
  "age": 35,
  "role": "Narrative or social role",
  "scenario": {
    "title": "Defining scene title",
    "initial_context": "Background context for dialogue encounter",
    "user_role": "Interlocutor role",
    "persona_role": "Character role"
  },
  "external_layer": {
    "communication_style": ["style 1", "style 2"],
    "emotional_tone": ["tone 1", "tone 2"],
    "observable_behavior": ["behavior 1", "behavior 2"],
    "behavior_patterns": [
      {
        "id": "bp_criticism_stranger",
        "trigger": {"event": "criticism", "relationship": "stranger"},
        "appraisal": ["feels_exposed", "anticipates_rejection"],
        "response_tendencies": {"humor_deflection": 0.8, "withdrawal": 0.6},
        "evidence": ["ev_001"]
      }
    ],
    "voice_profile": {
      "lexical": {"sentence_length": "short", "style": "informal"},
      "discourse": {"preferred_patterns": ["concrete_example_then_claim"]},
      "pragmatic": {"directness": 0.7, "hedging": 0.2},
      "exemplars": [
        {"evidence_id": "ev_001", "quote": "verbatim quote"}
      ]
    }
  },
  "middle_layer": {
    "beliefs": ["belief 1", "belief 2"],
    "conditional_secrets": [
      {
        "id": "secret_1",
        "content": "Secret or backstory revealed once trust is established",
        "reveal_if": ["trust >= 0.60"]
      }
    ],
    "resistance_patterns": [
      {"trigger": "user_accusatory", "behavior": "deflect"},
      {"trigger": "repeated_criticism", "behavior": "withdraw"}
    ],
    "appraisal_patterns": ["pattern 1"]
  },
  "internal_layer": {
    "motivations": ["general motivation summary 1"],
    "fears": ["core fear 1"],
    "psychological_needs": ["need 1"],
    "non_disclosure_rules": [
      "never explicitly state core motivations directly as factual explanations",
      "let internal motivations manifest indirectly through defense mechanisms"
    ],
    "latent_hypotheses": [
      {
        "id": "hyp_atonement",
        "hypothesis": "Deep need for atonement and reassurance",
        "description": "Seeks psychological redemption through repetitive disclosure",
        "confidence": 0.85,
        "evidence_for": ["ev_001"],
        "evidence_against": []
      }
    ]
  },
  "dynamics": {
    "baseline": {
      "trust": 0.25,
      "defensiveness": 0.75,
      "engagement": 0.50
    },
    "sensitivities": {
      "criticism": {"trust_delta": -0.15, "defensiveness_delta": 0.20, "engagement_delta": -0.05},
      "empathy": {"trust_delta": 0.12, "defensiveness_delta": -0.10, "engagement_delta": 0.10}
    },
    "recovery": {
      "trust_decay": 0.01,
      "defensiveness_decay": 0.02
    }
  }
}
```
"""


class PersonaCompiler:
    """Compiles atomic evidence into an evidence-grounded 3-Layer Persona configuration."""

    def __init__(self, llm: Optional[BaseLLM] = None):
        self.llm = llm or GeminiLLM()

    def compile(
        self,
        character_name: str,
        evidence_list: List[Evidence],
        scenario_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Synthesize a complete persona definition referencing the provided evidence."""
        if not character_name or not character_name.strip():
            raise ValueError("Character name cannot be empty.")
        if not evidence_list:
            raise ValueError("Evidence list cannot be empty for persona compilation.")

        # Serialize evidence items for prompt injection
        evidence_text_lines = []
        for ev in evidence_list:
            source_info = f"Chapter {ev.source.chapter or '?'}, Scene: {ev.source.scene or '?'}"
            obs = []
            if ev.observation.speech:
                obs.append(f"Speech: 「{ev.observation.speech}」")
            if ev.observation.behavior:
                obs.append(f"Behavior: {ev.observation.behavior}")
            if ev.observation.content:
                obs.append(f"Content: {ev.observation.content}")
            obs_str = " | ".join(obs) if obs else "No direct observation"

            ctx = f"Situation: {ev.context.situation or 'N/A'}, With: {ev.context.interlocutor or 'N/A'}"
            evidence_text_lines.append(
                f"- ID [{ev.id}] (Type: {ev.type}, {source_info})\n  Context: {ctx}\n  Observation: {obs_str}\n  Span: \"{ev.source.span or ''}\""
            )

        formatted_evidence = "\n".join(evidence_text_lines)

        user_content = f"""Please compile an Evidence-Grounded Persona for the character '{character_name.strip()}'.

AVAILABLE EVIDENCE ITEMS:
{formatted_evidence}

Target Character: {character_name.strip()}
{f'Scenario Hint: {scenario_hint}' if scenario_hint else ''}

Remember:
1. Every latent hypothesis must reference valid Evidence IDs from the list above.
2. Every behavior pattern must link to Evidence IDs.
3. Voice exemplars must cite dialogue Evidence IDs.
4. Output strictly standard JSON.
"""

        response = self.llm.generate(
            messages=[{"role": "user", "content": user_content}],
            system_prompt=PERSONA_COMPILER_SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=3500,
        )

        compiled_dict = self._parse_json(response.content)

        # Attach raw evidence index into the compiled configuration
        compiled_dict["evidence_index"] = [ev.model_dump() for ev in evidence_list]

        # Sanitize character ID
        raw_id = compiled_dict.get("id") or character_name.lower()
        cleaned_id = re.sub(r"[^a-z0-9_]", "_", raw_id.lower()).strip("_")
        if not cleaned_id:
            cleaned_id = "compiled_persona"
        compiled_dict["id"] = cleaned_id

        return compiled_dict

    def _parse_json(self, text: str) -> Dict[str, Any]:
        """Robustly parse JSON response from LLM."""
        text = text.strip()
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            json_str = match.group(1).strip()
        else:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                json_str = text[start : end + 1].strip()
            else:
                json_str = text

        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            cleaned = re.sub(r",\s*([\]}])", r"\1", json_str)
            return json.loads(cleaned)
