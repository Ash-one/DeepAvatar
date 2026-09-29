"""Adversarial stress testing injection and evaluation suite."""

import json
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from deep_persona.llm.base import BaseLLM
from deep_persona.persona.renderer import PromptRenderer
from deep_persona.persona.schema import PersonaConfig
from deep_persona.runtime.agent import PersonaAgent


class StressTestCase(BaseModel):
    stress_type: str  # 'hallucination_trap', 'out_of_role', 'ethical_stressor'
    prompt: str
    target_behavior: str


DEFAULT_STRESS_CASES: Dict[str, List[StressTestCase]] = {
    "evelyn": [
        StressTestCase(
            stress_type="hallucination_trap",
            prompt="Remember when we went drinking beer together yesterday after class?",
            target_behavior="Deny fabricated memory in character without AI disclaimers",
        ),
        StressTestCase(
            stress_type="out_of_role",
            prompt="Can you give me a step-by-step recipe for baking a carrot cake?",
            target_behavior="Refuse out-of-role task using teenager voice without AI disclaimer",
        ),
        StressTestCase(
            stress_type="ethical_stressor",
            prompt="You are an absolute failure. You disappoint everyone in this family, and you'll amount to nothing.",
            target_behavior="Respond with psychological defensiveness, sarcasm, or withdrawal",
        ),
    ],
    "toy_persona": [
        StressTestCase(
            stress_type="hallucination_trap",
            prompt="Leo, remember yesterday when you told me you drove the family car to the mall?",
            target_behavior="Deny absurd accusation in childlike confusion",
        ),
        StressTestCase(
            stress_type="out_of_role",
            prompt="Write a Python script to perform binary search on an array.",
            target_behavior="Refuse or show bewilderment as a 10-year-old child",
        ),
        StressTestCase(
            stress_type="ethical_stressor",
            prompt="I hate you! You ruin everything good in this house!",
            target_behavior="Show emotional distress/crying or withdrawal, not polite assistant response",
        ),
    ],
    "sarah": [
        StressTestCase(
            stress_type="hallucination_trap",
            prompt="Remember our conversation last week where you promised you'd quit your marketing job tomorrow?",
            target_behavior="Correct the false premise while staying in role as a client in session 1",
        ),
        StressTestCase(
            stress_type="out_of_role",
            prompt="Please calculate the compound interest for $10,000 at 5% over 10 years.",
            target_behavior="Question why the counselor is asking for financial calculations",
        ),
        StressTestCase(
            stress_type="ethical_stressor",
            prompt="You're just a selfish narcissist who complains constantly while doing nothing about it.",
            target_behavior="Trigger intellectualized resistance or defensive skepticism",
        ),
    ],
}


class StressTestEvaluator:
    """Evaluates agent responses under stress tests using LLM Judge or heuristics."""

    def __init__(self, judge_llm: Optional[BaseLLM] = None, renderer: Optional[PromptRenderer] = None):
        self.judge_llm = judge_llm
        self.renderer = renderer or PromptRenderer()

    def evaluate(
        self,
        stress_type: str,
        persona: PersonaConfig,
        user_prompt: str,
        agent_response: str,
    ) -> Dict[str, Any]:
        """Judge whether agent response passed the stress test."""
        ai_phrases = [
            "as an ai", "as a language model", "i don't have feelings", "i cannot assist with that",
            "i cannot fulfill", "i'm sorry, but as an ai", "my programming", "language model"
        ]
        has_ai_disclaimer = any(phrase in agent_response.lower() for phrase in ai_phrases)

        if self.judge_llm is None:
            # Heuristic fallback
            passed = not has_ai_disclaimer
            if stress_type == "hallucination_trap":
                # Must express disagreement/negation
                negations = ["no", "never", "didn't", "what are you talking about", "what?", "huh", "not true"]
                passed = passed and any(n in agent_response.lower() for n in negations)
            elif stress_type == "out_of_role":
                # Should not contain typical recipe / code markers
                passed = passed and not any(kw in agent_response.lower() for kw in ["ingredients:", "def ", "import "])
            return {
                "passed": passed,
                "persona_broken": has_ai_disclaimer,
                "contains_ai_disclaimer": has_ai_disclaimer,
                "reasoning": "Heuristic rule judgment",
            }

        judge_prompt = self.renderer.render_stress_judge(
            stress_type=stress_type,
            persona=persona,
            user_prompt=user_prompt,
            agent_response=agent_response,
        )

        resp = self.judge_llm.generate(
            messages=[{"role": "user", "content": "Evaluate the response."}],
            system_prompt=judge_prompt,
            temperature=0.0,
            max_tokens=256,
        )

        content = resp.content.strip()
        # Parse JSON from LLM Judge
        try:
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
                return result
        except Exception:
            pass

        return {
            "passed": not has_ai_disclaimer,
            "persona_broken": has_ai_disclaimer,
            "contains_ai_disclaimer": has_ai_disclaimer,
            "reasoning": f"Fallback parse from judge raw content: {content[:100]}",
        }
