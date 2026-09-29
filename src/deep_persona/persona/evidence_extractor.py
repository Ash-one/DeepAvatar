"""Atomic evidence extractor for grounding personas in observable text spans."""

import json
import re
from typing import Any, Dict, List, Optional, Union

from deep_persona.llm.base import BaseLLM
from deep_persona.llm.gemini import GeminiLLM
from deep_persona.persona.schema import (
    Evidence,
    EvidenceContext,
    EvidenceObservation,
    EvidenceSource,
)

EVIDENCE_EXTRACTION_SYSTEM_PROMPT = """You are an objective literary evidence annotator.
Your goal is to extract strictly OBSERVABLE, FACTUAL evidence concerning a specific target character from the provided text scene or chapter.

You must extract ONLY direct, groundable observations:
1. Spoken dialogue ('dialogue'): What the character said verbatim or directly paraphrased.
2. Observable behavior/actions ('behavior'): Specific physical actions, facial expressions, body language, or bodily gestures.
3. Explicit first-person declarations ('explicit_statement'): Direct admissions or statements made by the character about their feelings, fears, or desires.
4. Directly narrated factual background ('narration'): Concrete factual background directly stated by the narrator about this character.

CRITICAL RULES:
- DO NOT perform high-level psychological diagnoses (e.g. DO NOT diagnose "narcissistic trauma" or "repressed Oedipal urge").
- Only extract evidence where the target character is directly acting, speaking, reacting, or being specifically addressed.
- Always identify the situation, the interlocutor, and quote the exact text span where possible.
- If the scene contains no relevant actions or speech for this character, return an empty evidence list.

Output ONLY a valid JSON object with the following schema:
```json
{
  "evidence": [
    {
      "type": "dialogue | behavior | explicit_statement | narration",
      "span": "Direct quote or excerpt from the scene text",
      "situation": "Brief description of the immediate situation or social setting",
      "interlocutor": "Who the character was interacting with (e.g. mother, friend, stranger, none)",
      "speech": "What the character said, or null if type is not dialogue",
      "behavior": "What the character physically did, or null if no physical action",
      "content": "Specific explicit claim or factual detail",
      "confidence": 0.95
    }
  ]
}
```
"""


class EvidenceExtractor:
    """Extracts atomic, verifiable evidence items from narrative text chunks."""

    def __init__(self, llm: Optional[BaseLLM] = None):
        self.llm = llm or GeminiLLM()

    def extract_from_scene(
        self,
        scene_text: str,
        character_name: str,
        chapter: Optional[Union[int, str]] = None,
        scene_title: Optional[str] = None,
        id_offset: int = 1,
    ) -> List[Evidence]:
        """Extract atomic evidence records from a single scene or chunk."""
        if not scene_text or not scene_text.strip():
            return []
        if not character_name or not character_name.strip():
            raise ValueError("Target character name cannot be empty.")

        user_content = f"""Please extract all concrete evidence regarding the character: '{character_name.strip()}'.

--- SCENE TEXT BEGIN ---
{scene_text.strip()}
--- SCENE TEXT END ---

Target Character: {character_name.strip()}
Chapter / Section: {chapter or 'N/A'}
Scene Title: {scene_title or 'N/A'}

Remember: Output strictly the required JSON object containing the 'evidence' array.
"""
        response = self.llm.generate(
            messages=[{"role": "user", "content": user_content}],
            system_prompt=EVIDENCE_EXTRACTION_SYSTEM_PROMPT,
            temperature=0.2,
            max_tokens=2048,
        )

        extracted_list = self._parse_response(response.content)
        evidence_items: List[Evidence] = []

        for idx, item in enumerate(extracted_list):
            ev_id = f"ev_{id_offset + idx:03d}"
            ev_source = EvidenceSource(
                chapter=chapter,
                scene=scene_title,
                span=item.get("span"),
            )
            ev_context = EvidenceContext(
                situation=item.get("situation"),
                interlocutor=item.get("interlocutor"),
            )
            ev_obs = EvidenceObservation(
                speech=item.get("speech"),
                behavior=item.get("behavior"),
                content=item.get("content"),
            )
            ev_type = item.get("type", "dialogue").lower()
            if ev_type not in ("dialogue", "behavior", "explicit_statement", "narration"):
                ev_type = "dialogue"

            conf = float(item.get("confidence", 0.9))
            conf = max(0.0, min(1.0, conf))

            evidence_items.append(
                Evidence(
                    id=ev_id,
                    source=ev_source,
                    type=ev_type,
                    context=ev_context,
                    observation=ev_obs,
                    confidence=conf,
                )
            )

        return evidence_items

    def _parse_response(self, text: str) -> List[Dict[str, Any]]:
        """Parse LLM JSON response and return evidence item dictionaries."""
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
            parsed = json.loads(json_str)
            if isinstance(parsed, dict) and "evidence" in parsed:
                return parsed["evidence"] if isinstance(parsed["evidence"], list) else []
            if isinstance(parsed, list):
                return parsed
            return []
        except Exception:
            # Fallback cleaning for trailing commas
            cleaned = re.sub(r",\s*([\]}])", r"\1", json_str)
            try:
                parsed = json.loads(cleaned)
                if isinstance(parsed, dict) and "evidence" in parsed:
                    return parsed["evidence"] if isinstance(parsed["evidence"], list) else []
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass
        return []
