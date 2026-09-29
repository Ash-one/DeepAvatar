"""Orchestrator for Evidence-Grounded Persona construction from narrative stories."""

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from deep_persona.llm.base import BaseLLM
from deep_persona.llm.gemini import GeminiLLM
from deep_persona.persona.compiler import PersonaCompiler
from deep_persona.persona.critic import ConsistencyCritic, CritiqueReport
from deep_persona.persona.evidence_extractor import EvidenceExtractor
from deep_persona.persona.schema import Evidence, EvidenceContext, EvidenceObservation, EvidenceSource

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


def resolve_character_aliases(name: str, aliases: Optional[List[str]] = None) -> List[str]:
    """Resolve a character's primary name and alternative aliases (e.g. short names or pronouns)."""
    candidates = [name.strip()]
    if aliases:
        candidates.extend([a.strip() for a in aliases if a.strip()])

    # Split compound titles or parenthetical aliases e.g. "大庭叶藏 (叶藏)"
    sub_parts = re.split(r"[/|,\(\)（）\s]+", name)
    for p in sub_parts:
        clean = p.strip()
        if len(clean) >= 2 and clean not in candidates:
            candidates.append(clean)
    return candidates


def segment_narrative(text: str, max_chunk_size: int = 5000) -> List[Dict[str, Any]]:
    """Segment narrative text into coherent scenes or chapter chunks."""
    text = text.strip()
    if not text:
        return []

    # Look for obvious chapter / section headings
    chapter_pattern = r"(?:\n|^)(第[0-9一二三四五六七八九十百]+[章回节]|Chapter\s+[0-9]+|手记之[一二三四五六七八九十]+|序|后记|---|\*\*\*)\s*"
    splits = re.split(chapter_pattern, text)

    if len(splits) > 1:
        chunks = []
        preamble = splits[0].strip()
        if preamble and len(preamble) > 50:
            chunks.append({"chapter": 1, "scene": "Prologue / Background", "text": preamble})

        idx = len(chunks) + 1
        for i in range(1, len(splits), 2):
            title = splits[i].strip()
            content = splits[i + 1].strip() if i + 1 < len(splits) else ""
            if not content or len(content) < 20:
                continue

            if len(content) <= max_chunk_size:
                chunks.append({"chapter": idx, "scene": title, "text": content})
                idx += 1
            else:
                # Sub-chunk by paragraphs without breaking sentences
                paras = content.split("\n\n")
                cur = []
                cur_len = 0
                part = 1
                for p in paras:
                    pc = p.strip()
                    if not pc:
                        continue
                    if cur_len + len(pc) > max_chunk_size and cur:
                        chunks.append({
                            "chapter": idx,
                            "scene": f"{title} (Part {part})",
                            "text": "\n\n".join(cur),
                        })
                        idx += 1
                        part += 1
                        cur = [pc]
                        cur_len = len(pc)
                    else:
                        cur.append(pc)
                        cur_len += len(pc)
                if cur:
                    chunks.append({
                        "chapter": idx,
                        "scene": f"{title} (Part {part})",
                        "text": "\n\n".join(cur),
                    })
                    idx += 1
        return chunks

    # Fallback to paragraph-based chunking without breaking sentences
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = []
    current_length = 0
    chunk_idx = 1

    for para in paragraphs:
        para_clean = para.strip()
        if not para_clean:
            continue
        if current_length + len(para_clean) > max_chunk_size and current_chunk:
            chunks.append({
                "chapter": chunk_idx,
                "scene": f"Scene {chunk_idx}",
                "text": "\n\n".join(current_chunk),
            })
            chunk_idx += 1
            current_chunk = [para_clean]
            current_length = len(para_clean)
        else:
            current_chunk.append(para_clean)
            current_length += len(para_clean)

    if current_chunk:
        chunks.append({
            "chapter": chunk_idx,
            "scene": f"Scene {chunk_idx}",
            "text": "\n\n".join(current_chunk),
        })

    return chunks


class StoryPersonaExtractor:
    """Orchestrates multi-stage evidence extraction, compilation, and critique."""

    def __init__(
        self,
        llm: Optional[BaseLLM] = None,
        evidence_extractor: Optional[EvidenceExtractor] = None,
        compiler: Optional[PersonaCompiler] = None,
        critic: Optional[ConsistencyCritic] = None,
    ):
        self.llm = llm or GeminiLLM()
        self.evidence_extractor = evidence_extractor or EvidenceExtractor(llm=self.llm)
        self.compiler = compiler or PersonaCompiler(llm=self.llm)
        self.critic = critic or ConsistencyCritic(llm=self.llm)

    def extract_from_story(
        self,
        story_text: str,
        character_name: str,
        max_chars: Optional[int] = 50000,
        character_aliases: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Extract structured persona fields using multi-stage evidence pipeline with backward compatibility."""
        if not story_text or not story_text.strip():
            raise ValueError("Story text cannot be empty.")
        if not character_name or not character_name.strip():
            raise ValueError("Target character name cannot be empty.")

        target_char = character_name.strip()
        match_names = resolve_character_aliases(target_char, character_aliases)
        raw_text = story_text[:max_chars].strip() if max_chars else story_text.strip()

        # Step 1: Segment text into scenes
        chunks = segment_narrative(raw_text)
        if not chunks:
            chunks = [{"chapter": 1, "scene": "Scene 1", "text": raw_text}]

        # Step 2: Extract atomic evidence across scenes
        all_evidence: List[Evidence] = []
        ev_id_offset = 1
        for chunk in chunks:
            # Check if character or any alias is mentioned in chunk to optimize extraction
            if any(name in chunk["text"] for name in match_names) or len(chunks) == 1:
                evs = self.evidence_extractor.extract_from_scene(
                    scene_text=chunk["text"],
                    character_name=target_char,
                    chapter=chunk.get("chapter"),
                    scene_title=chunk.get("scene"),
                    id_offset=ev_id_offset,
                )
                all_evidence.extend(evs)
                ev_id_offset += len(evs)

        # Step 3: If evidence extraction produced items, compile and critique
        if all_evidence:
            compiled = self.compiler.compile(
                character_name=target_char,
                evidence_list=all_evidence,
            )
            refined_persona, critique_report = self.critic.audit(
                compiled_persona=compiled,
                evidence_list=all_evidence,
                run_llm_critic=False,  # default fast local critic during extraction
            )
            return self._format_as_flat_and_nested_dict(refined_persona, all_evidence, target_char)

        # Fallback Step 4: If no atomic evidence parsed (e.g. mocked single-shot LLM in legacy tests)
        user_content = f"""Please analyze the following narrative text and extract a deep psychological persona configuration for the character: '{target_char}'.

--- NARRATIVE TEXT BEGIN ---
{raw_text}
--- NARRATIVE TEXT END ---

Target Character: {target_char}

Remember: Respond strictly with the required JSON object.
"""
        response = self.llm.generate(
            messages=[{"role": "user", "content": user_content}],
            system_prompt=PERSONA_EXTRACTION_SYSTEM_PROMPT,
            temperature=0.4,
            max_tokens=2500,
        )

        extracted_dict = extract_json_from_llm_response(response.content)

        # Sanitize id
        raw_id = extracted_dict.get("id") or target_char.lower()
        cleaned_id = re.sub(r"[^a-z0-9_]", "_", raw_id.lower()).strip("_")
        if not cleaned_id:
            cleaned_id = "extracted_persona"
        extracted_dict["id"] = cleaned_id

        return extracted_dict

    def extract_with_evidence(
        self,
        story_text: str,
        character_name: str,
        max_chars: Optional[int] = None,
        character_aliases: Optional[List[str]] = None,
        run_llm_critic: bool = True,
    ) -> Tuple[Dict[str, Any], List[Evidence], CritiqueReport]:
        """Full evidence-grounded pipeline returning compiled persona, raw evidence, and critique report."""
        if not story_text or not story_text.strip():
            raise ValueError("Story text cannot be empty.")
        if not character_name or not character_name.strip():
            raise ValueError("Target character name cannot be empty.")

        target_char = character_name.strip()
        match_names = resolve_character_aliases(target_char, character_aliases)
        raw_text = story_text[:max_chars].strip() if max_chars else story_text.strip()

        chunks = segment_narrative(raw_text)
        if not chunks:
            chunks = [{"chapter": 1, "scene": "Scene 1", "text": raw_text}]

        all_evidence: List[Evidence] = []
        ev_id_offset = 1
        for chunk in chunks:
            if any(name in chunk["text"] for name in match_names) or len(chunks) == 1:
                evs = self.evidence_extractor.extract_from_scene(
                    scene_text=chunk["text"],
                    character_name=target_char,
                    chapter=chunk.get("chapter"),
                    scene_title=chunk.get("scene"),
                    id_offset=ev_id_offset,
                )
                all_evidence.extend(evs)
                ev_id_offset += len(evs)

        if not all_evidence:
            # Create at least one fallback evidence anchor from text
            all_evidence.append(
                Evidence(
                    id="ev_001",
                    source=EvidenceSource(chapter=1, scene="Overview", span=raw_text[:200]),
                    type="narration",
                    context=EvidenceContext(situation="General narrative context"),
                    observation=EvidenceObservation(content=f"Narrative regarding {target_char}"),
                    confidence=0.8,
                )
            )

        compiled = self.compiler.compile(
            character_name=target_char,
            evidence_list=all_evidence,
        )

        refined_persona, critique_report = self.critic.audit(
            compiled_persona=compiled,
            evidence_list=all_evidence,
            run_llm_critic=run_llm_critic,
        )

        final_dict = self._format_as_flat_and_nested_dict(refined_persona, all_evidence, target_char)
        return final_dict, all_evidence, critique_report

    def _format_as_flat_and_nested_dict(
        self,
        persona: Dict[str, Any],
        evidence_list: List[Evidence],
        character_name: str,
    ) -> Dict[str, Any]:
        """Harmonize dictionary so both legacy flat keys and v2 nested keys are populated."""
        res = dict(persona)

        # Ensure top-level identity fields exist
        if "id" not in res:
            res["id"] = re.sub(r"[^a-z0-9_]", "_", character_name.lower()).strip("_")
        if "name" not in res:
            res["name"] = character_name

        # Scenario unrolling if nested
        scenario = res.get("scenario", {})
        if isinstance(scenario, dict):
            res["scenario_title"] = scenario.get("title", f"{character_name}'s Scene")
            res["scenario_initial_context"] = scenario.get("initial_context", "Encounter begins.")
            res["scenario_user_role"] = scenario.get("user_role", "interlocutor")
            res["scenario_persona_role"] = scenario.get("persona_role", character_name)

        # External layer unrolling
        ext = res.get("external_layer", {})
        if isinstance(ext, dict):
            res["communication_style"] = ext.get("communication_style", [])
            res["emotional_tone"] = ext.get("emotional_tone", [])
            res["observable_behavior"] = ext.get("observable_behavior", [])

        # Middle layer unrolling
        mid = res.get("middle_layer", {})
        if isinstance(mid, dict):
            res["beliefs"] = mid.get("beliefs", [])
            res["conditional_secrets"] = mid.get("conditional_information", [])

        # Internal layer unrolling
        intl = res.get("internal_layer", {})
        if isinstance(intl, dict):
            res["motivations"] = intl.get("motivations", [])
            res["fears"] = intl.get("fears", [])
            res["psychological_needs"] = intl.get("psychological_needs", [])

        # Ensure evidence_index is attached
        res["evidence_index"] = [ev.model_dump() for ev in evidence_list]

        return res
