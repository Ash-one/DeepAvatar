"""Consistency Critic: Audits and calibrates evidence citations, detects contradictions, and validates persona grounding."""

import json
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field

from deep_persona.llm.base import BaseLLM
from deep_persona.llm.gemini import GeminiLLM
from deep_persona.persona.schema import Evidence


class CritiqueReport(BaseModel):
    is_valid: bool = True
    grounded_ratio: float = 1.0
    total_hypotheses: int = 0
    grounded_hypotheses: int = 0
    invalid_evidence_ids: List[str] = Field(default_factory=list)
    contradictions: List[str] = Field(default_factory=list)
    unsupported_claims: List[str] = Field(default_factory=list)
    calibrated_hypotheses_count: int = 0
    suggestions: List[str] = Field(default_factory=list)


CRITIC_SYSTEM_PROMPT = """You are a rigorous psychometric consistency auditor.
Your job is to examine an induced Persona against the authoritative list of atomic evidence to detect:
1. Contradictions: Claims in the persona directly contradicted by source evidence.
2. Overgeneralizations: Sweeping internal traits asserted without sufficient textual support.
3. Negative Evidence: Behaviors or speech in the evidence that contradict or qualify asserted traits.

Respond ONLY with a valid JSON object matching:
```json
{
  "contradictions": ["description of contradiction 1"],
  "unsupported_claims": ["claim lacking evidence"],
  "suggested_counter_evidence": [
    {
      "hypothesis_id": "hyp_id",
      "counter_evidence_id": "ev_00X",
      "reason": "Why this evidence contradicts or limits the hypothesis"
    }
  ],
  "suggestions": ["suggestion for improving grounding"]
}
```
"""


class ConsistencyCritic:
    """Audits persona grounding against the evidence store and resolves contradictions."""

    def __init__(self, llm: Optional[BaseLLM] = None):
        self.llm = llm or GeminiLLM()

    def audit(
        self,
        compiled_persona: Dict[str, Any],
        evidence_list: List[Evidence],
        run_llm_critic: bool = True,
    ) -> Tuple[Dict[str, Any], CritiqueReport]:
        """Perform mechanical and semantic grounding audit on a compiled persona."""
        valid_ev_ids: Set[str] = {ev.id for ev in evidence_list}
        invalid_ids: List[str] = []
        contradictions: List[str] = []
        unsupported: List[str] = []
        suggestions: List[str] = []

        internal = compiled_persona.get("internal_layer", {})
        hypotheses = internal.get("latent_hypotheses", [])
        total_hyp = len(hypotheses)
        grounded_hyp = 0
        calibrated_count = 0

        # 1. Deterministic citation validation & confidence calibration
        refined_hypotheses = []
        for hyp in hypotheses:
            ev_for = hyp.get("evidence_for", [])
            ev_against = hyp.get("evidence_against", [])

            # Check invalid citations
            cleaned_for = []
            for ev_id in ev_for:
                if ev_id in valid_ev_ids:
                    cleaned_for.append(ev_id)
                else:
                    invalid_ids.append(ev_id)

            cleaned_against = []
            for ev_id in ev_against:
                if ev_id in valid_ev_ids:
                    cleaned_against.append(ev_id)
                else:
                    invalid_ids.append(ev_id)

            hyp["evidence_for"] = cleaned_for
            hyp["evidence_against"] = cleaned_against

            # Calibrate confidence
            curr_conf = float(hyp.get("confidence", 0.7))
            if not cleaned_for:
                curr_conf = min(curr_conf, 0.40)
                unsupported.append(f"Hypothesis '{hyp.get('id')}' lacks supporting evidence citations.")
            else:
                grounded_hyp += 1
                # Penalize if counter-evidence exists
                if cleaned_against:
                    curr_conf = max(0.20, curr_conf - 0.20 * len(cleaned_against))

            hyp["confidence"] = round(curr_conf, 2)
            calibrated_count += 1
            refined_hypotheses.append(hyp)

        internal["latent_hypotheses"] = refined_hypotheses

        # 2. Check Behavior Patterns
        external = compiled_persona.get("external_layer", {})
        patterns = external.get("behavior_patterns", [])
        for bp in patterns:
            bp_ev = bp.get("evidence", [])
            cleaned_bp_ev = []
            for ev_id in bp_ev:
                if ev_id in valid_ev_ids:
                    cleaned_bp_ev.append(ev_id)
                else:
                    invalid_ids.append(ev_id)
            bp["evidence"] = cleaned_bp_ev

        # 3. Optional LLM semantic contradiction audit
        if run_llm_critic and evidence_list and total_hyp > 0:
            try:
                llm_critique = self._query_llm_critic(compiled_persona, evidence_list)
                contradictions.extend(llm_critique.get("contradictions", []))
                unsupported.extend(llm_critique.get("unsupported_claims", []))
                suggestions.extend(llm_critique.get("suggestions", []))

                # Inject newly discovered counter-evidence if any
                for counter in llm_critique.get("suggested_counter_evidence", []):
                    target_hyp_id = counter.get("hypothesis_id")
                    counter_id = counter.get("counter_evidence_id")
                    if counter_id in valid_ev_ids:
                        for hyp in internal.get("latent_hypotheses", []):
                            if hyp.get("id") == target_hyp_id:
                                if counter_id not in hyp["evidence_against"]:
                                    hyp["evidence_against"].append(counter_id)
                                    hyp["confidence"] = max(0.10, round(hyp["confidence"] - 0.15, 2))
            except Exception:
                # LLM critic error is non-fatal; deterministic checks hold
                pass

        grounded_ratio = (grounded_hyp / total_hyp) if total_hyp > 0 else 1.0
        is_valid = len(invalid_ids) == 0 and len(contradictions) == 0

        report = CritiqueReport(
            is_valid=is_valid,
            grounded_ratio=round(grounded_ratio, 2),
            total_hypotheses=total_hyp,
            grounded_hypotheses=grounded_hyp,
            invalid_evidence_ids=list(set(invalid_ids)),
            contradictions=contradictions,
            unsupported_claims=unsupported,
            calibrated_hypotheses_count=calibrated_count,
            suggestions=suggestions,
        )

        return compiled_persona, report

    def _query_llm_critic(
        self,
        compiled_persona: Dict[str, Any],
        evidence_list: List[Evidence],
    ) -> Dict[str, Any]:
        """Invoke LLM to audit semantic contradictions."""
        ev_summary = "\n".join(
            f"[{ev.id}] ({ev.type}): {ev.observation.speech or ev.observation.behavior or ev.observation.content}"
            for ev in evidence_list[:30]  # cap to top 30 evidence items for audit prompt
        )

        hyp_summary = "\n".join(
            f"[{h.get('id')}]: {h.get('hypothesis')} (supports: {h.get('evidence_for')})"
            for h in compiled_persona.get("internal_layer", {}).get("latent_hypotheses", [])
        )

        user_content = f"""Persona Internal Hypotheses:
{hyp_summary}

Authoritative Evidence Observations:
{ev_summary}

Please audit the hypotheses against the observations for contradictions, overgeneralizations, or missing counter-evidence.
"""
        response = self.llm.generate(
            messages=[{"role": "user", "content": user_content}],
            system_prompt=CRITIC_SYSTEM_PROMPT,
            temperature=0.2,
            max_tokens=1500,
        )

        text = response.content.strip()
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        json_str = match.group(1).strip() if match else text
        try:
            return json.loads(json_str)
        except Exception:
            return {}
