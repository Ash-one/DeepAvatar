"""Extractor for constructing 3-Layer Deep Persona configurations from narrative texts."""

import json
import re
from typing import Any, Dict, Optional

from deep_persona.llm.base import BaseLLM
from deep_persona.llm.gemini import GeminiLLM

PERSONA_EXTRACTION_SYSTEM_PROMPT = """You are an expert in literary character analysis and computational psychometrics based on the 3-Layer Persona Cognitive Architecture:
1. External Layer: Directly observable communication style, emotional tone, and embodied behaviors.
2. Middle Layer: Beliefs and conditional secrets (information revealed only after trust is established).
3. Internal Layer: Deep unconscious motivations, core fears, and psychological needs (which the agent must never verbalize directly).

Your task is to analyze the provided story/narrative text and construct a comprehensive, faithful Deep Persona profile for the specified character.

You MUST output ONLY a valid JSON object with the following schema, and no extra markdown commentary outside the JSON:
```json
{
  "id": "short_lowercase_english_id_with_underscores (e.g. hamlet, sherlock, xianglin_sao)",
  "name": "Character Name",
  "age": 30,
  "role": "Societal or narrative role",
  "scenario_title": "Defining scene or conflict title",
  "scenario_initial_context": "Detailed description of a defining scene where a confrontation/dialogue begins",
  "scenario_user_role": "The role of the interlocutor in this scene (e.g. detective, family member, superior)",
  "scenario_persona_role": "This character's role in the scene",
  "communication_style": ["style 1", "style 2"],
  "emotional_tone": ["tone 1", "tone 2"],
  "observable_behavior": ["embodied behavior 1", "embodied behavior 2"],
  "beliefs": ["belief 1", "belief 2"],
  "conditional_secrets": [
    {
      "id": "secret_id",
      "content": "A hidden backstory fact or vulnerability revealed only when trust is built",
      "reveal_if": ["trust >= 0.50"]
    }
  ],
  "motivations": ["motivation_1", "motivation_2"],
  "fears": ["fear_1", "fear_2"],
  "psychological_needs": ["need_1", "need_2"]
}
```
CRITICAL FORMAT RULES:
- Output strictly standard RFC 8259 JSON without trailing commas.
- If you use quotation marks inside string values, use Chinese quotation marks (「」 or 『』) or single quotes ('), NEVER unescaped double quotes (\").
If the story is in Chinese, provide the dialogue habits, context, and descriptions naturally in Chinese so the persona sounds authentic in Chinese dialogues, with a clean lowercase English ID.
"""


def extract_json_from_llm_response(text: str) -> Dict[str, Any]:
    """Robustly extract JSON dictionary from model response."""
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

    # Attempt 1: Direct JSON parse
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    # Attempt 2: Strip trailing commas
    cleaned = re.sub(r",\s*([\]}])", r"\1", json_str)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Attempt 3: Fix unescaped internal quotes on key-value lines
    def fix_line_quotes(line: str) -> str:
        kv_match = re.match(r'^(\s*"[^"]+"\s*:\s*")(.*)("\s*,?\s*)$', line)
        if kv_match:
            prefix, content, suffix = kv_match.groups()
            if '"' in content:
                content = content.replace('"', "'")
            return f"{prefix}{content}{suffix}"
        return line

    repaired_lines = [fix_line_quotes(l) for l in cleaned.splitlines()]
    repaired_json = "\n".join(repaired_lines)
    try:
        return json.loads(repaired_json)
    except json.JSONDecodeError as err:
        raise ValueError(f"Failed to parse extracted JSON from model response: {err}")


class StoryPersonaExtractor:
    """Extracts structured personas from narrative stories."""

    def __init__(self, llm: Optional[BaseLLM] = None):
        self.llm = llm or GeminiLLM()

    def extract_from_story(
        self,
        story_text: str,
        character_name: str,
        max_chars: int = 50000,
    ) -> Dict[str, Any]:
        """Analyze story and return structured persona fields."""
        if not story_text or not story_text.strip():
            raise ValueError("Story text cannot be empty.")
        if not character_name or not character_name.strip():
            raise ValueError("Target character name cannot be empty.")

        # Truncate if story text exceeds safe limits
        truncated_text = story_text[:max_chars].strip()
        if len(story_text) > max_chars:
            truncated_text += "\n\n[... Narrative truncated due to length ...]"

        user_content = f"""Please analyze the following narrative text and extract a deep psychological persona configuration for the character: '{character_name.strip()}'.

--- NARRATIVE TEXT BEGIN ---
{truncated_text}
--- NARRATIVE TEXT END ---

Target Character: {character_name.strip()}

Remember: Respond strictly with the required JSON object.
"""

        response = self.llm.generate(
            messages=[{"role": "user", "content": user_content}],
            system_prompt=PERSONA_EXTRACTION_SYSTEM_PROMPT,
            temperature=0.4,
            max_tokens=2500,
        )

        extracted_dict = extract_json_from_llm_response(response.content)

        # Fallback sanitize id
        raw_id = extracted_dict.get("id") or character_name.lower()
        cleaned_id = re.sub(r"[^a-z0-9_]", "_", raw_id.lower()).strip("_")
        if not cleaned_id:
            cleaned_id = "extracted_persona"
        extracted_dict["id"] = cleaned_id

        return extracted_dict
