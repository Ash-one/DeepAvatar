"""Test script for Phase A Evidence-Grounded Persona construction on 人间失格."""

import json
import sys
import time
from pathlib import Path
import yaml

from deep_persona.llm.gemini import GeminiLLM
from deep_persona.persona.extractor import StoryPersonaExtractor
from deep_persona.persona.schema import PersonaConfig


def main():
    story_path = Path("data/stories/人间失格.txt")
    if not story_path.exists():
        print(f"Error: {story_path} not found.")
        sys.exit(1)

    print("=" * 60)
    print("Testing Phase A: Evidence-Grounded Persona Extraction")
    print("Source: data/stories/人间失格.txt")
    print("Character: 大庭叶藏 (Yozo Oba)")
    print("=" * 60)

    with open(story_path, "r", encoding="utf-8") as f:
        full_text = f.read()

    # We extract from the core defining sections: 序 (Three Photographs) + 手记之一 + 手记之二(Part 1 - Takeichi incident)
    # This covers roughly 15,000 characters spanning the key psychological formative events.
    from deep_persona.persona.extractor import segment_narrative

    all_chunks = segment_narrative(full_text)
    # Select chunks 1, 2, 3, 4 (序, 手记之一 Part 1 & 2, 手记之二 Part 1)
    selected_chunks = [c for c in all_chunks if c["scene"].startswith("序") or "手记之一" in c["scene"] or "手记之二 (Part 1)" in c["scene"]]
    selected_text = "\n\n".join(f"## {c['scene']}\n{c['text']}" for c in selected_chunks)

    print(f"Selected {len(selected_chunks)} core narrative scenes ({len(selected_text)} characters):")
    for c in selected_chunks:
        print(f" - {c['scene']} ({len(c['text'])} chars)")

    print("\nInitializing StoryPersonaExtractor with real Gemini LLM...")
    llm = GeminiLLM()
    extractor = StoryPersonaExtractor(llm=llm)

    start_time = time.time()
    print("Running extract_with_evidence() pipeline...")
    persona_dict, evidence_list, critique_report = extractor.extract_with_evidence(
        story_text=selected_text,
        character_name="大庭叶藏",
        character_aliases=["叶藏", "我"],
        run_llm_critic=True,
    )
    elapsed = time.time() - start_time

    print("\n" + "=" * 60)
    print(f"Extraction Pipeline Completed in {elapsed:.2f}s")
    print("=" * 60)

    print(f"\n1. Extracted Atomic Evidence: {len(evidence_list)} items")
    for ev in evidence_list[:5]:
        print(f" - [{ev.id}] Type: {ev.type} | Conf: {ev.confidence}")
        print(f"   Scene: {ev.source.scene} | Context: {ev.context.situation}")
        if ev.observation.speech:
            print(f"   Speech: 「{ev.observation.speech}」")
        if ev.observation.behavior:
            print(f"   Behavior: {ev.observation.behavior}")
        if ev.source.span:
            span_preview = ev.source.span[:70] + "..." if len(ev.source.span) > 70 else ev.source.span
            print(f"   Span: \"{span_preview}\"")
        print()

    if len(evidence_list) > 5:
        print(f" ... and {len(evidence_list) - 5} more evidence items.")

    print("\n2. Consistency Critic Report:")
    print(f" - Is Valid: {critique_report.is_valid}")
    print(f" - Grounded Ratio: {critique_report.grounded_ratio:.2%}")
    print(f" - Total Hypotheses: {critique_report.total_hypotheses}")
    print(f" - Grounded Hypotheses: {critique_report.grounded_hypotheses}")
    print(f" - Invalid Citations: {critique_report.invalid_evidence_ids}")
    print(f" - Contradictions: {critique_report.contradictions}")
    print(f" - Calibrated Count: {critique_report.calibrated_hypotheses_count}")
    print(f" - Suggestions: {critique_report.suggestions}")

    print("\n3. Compiled 3-Layer Persona Architecture:")
    print(f" - Character ID: {persona_dict.get('id')}")
    print(f" - Name: {persona_dict.get('name')}")
    print(f" - Age: {persona_dict.get('persona', {}).get('age') or persona_dict.get('age')}")
    print(f" - Role: {persona_dict.get('persona', {}).get('role') or persona_dict.get('role')}")

    scenario = persona_dict.get("scenario", {})
    print(f" - Scenario: {scenario.get('title')} (User role: {scenario.get('user_role')})")

    ext_layer = persona_dict.get("external_layer", {})
    behavior_patterns = ext_layer.get("behavior_patterns", [])
    voice_profile = ext_layer.get("voice_profile", {})
    print(f"\n [External Layer]")
    print(f" - Communication Style: {ext_layer.get('communication_style')}")
    print(f" - Emotional Tone: {ext_layer.get('emotional_tone')}")
    print(f" - Behavior Patterns ({len(behavior_patterns)} patterns):")
    for bp in behavior_patterns:
        print(f"   * {bp.get('id')}: Trigger={bp.get('trigger')}, Evidence={bp.get('evidence')}")
    if voice_profile:
        print(f" - Voice Profile:")
        print(f"   * Lexical: {voice_profile.get('lexical')}")
        print(f"   * Discourse: {voice_profile.get('discourse')}")
        exemplars = voice_profile.get("exemplars", [])
        print(f"   * Exemplars ({len(exemplars)}): {[e.get('quote') for e in exemplars]}")

    mid_layer = persona_dict.get("middle_layer", {})
    print(f"\n [Middle Layer]")
    print(f" - Beliefs: {mid_layer.get('beliefs')}")
    print(f" - Conditional Information: {len(mid_layer.get('conditional_information', []))} items")
    print(f" - Resistance Patterns: {mid_layer.get('resistance_patterns')}")

    intl_layer = persona_dict.get("internal_layer", {})
    hypotheses = intl_layer.get("latent_hypotheses", [])
    print(f"\n [Internal Layer]")
    print(f" - Motivations: {intl_layer.get('motivations')}")
    print(f" - Fears: {intl_layer.get('fears')}")
    print(f" - Latent Hypotheses ({len(hypotheses)} hypotheses):")
    for hyp in hypotheses:
        print(f"   * ID [{hyp.get('id')}] (Conf: {hyp.get('confidence')}): {hyp.get('hypothesis')}")
        print(f"     Evidence For: {hyp.get('evidence_for')}")
        print(f"     Evidence Against: {hyp.get('evidence_against')}")

    dynamics = persona_dict.get("dynamics", {})
    print(f"\n [Dynamics]")
    print(f" - Baseline: {dynamics.get('baseline')}")
    print(f" - Sensitivities: {list(dynamics.get('sensitivities', {}).keys())}")

    # Validate against Pydantic schema
    print("\n4. Schema Validation (Pydantic PersonaConfig):")
    try:
        validated_config = PersonaConfig.model_validate(persona_dict)
        print(" [SUCCESS] Successfully validated against PersonaConfig schema!")
    except Exception as err:
        print(f" [FAILED] Schema validation error: {err}")
        return

    # Save to personas/dazai_osamu_evidence_grounded.yaml
    output_path = Path("personas/dazai_yozo_grounded.yaml")
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(persona_dict, f, allow_unicode=True, sort_keys=False)
    print(f"\n Saved generated persona configuration to: {output_path}")

    # Save evidence and critique report
    evidence_output_path = Path("results/dazai_yozo_evidence.json")
    evidence_output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(evidence_output_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "evidence": [ev.model_dump() for ev in evidence_list],
                "critique": critique_report.model_dump(),
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f" Saved evidence and critique artifacts to: {evidence_output_path}")


if __name__ == "__main__":
    main()
