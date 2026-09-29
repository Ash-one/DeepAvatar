#!/usr/bin/env python3
"""Run adversarial stress testing suite on persona."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from deep_persona.llm.gemini import GeminiLLM, MockLLM
from deep_persona.persona.loader import load_persona
from deep_persona.runtime.agent import PersonaAgent
from deep_persona.simulation.stress_test import (
    DEFAULT_STRESS_CASES,
    StressTestCase,
    StressTestEvaluator,
)


def main():
    parser = argparse.ArgumentParser(description="Run Adversarial Stress Tests.")
    parser.add_argument("--persona", type=str, default="personas/evelyn.yaml", help="Path to persona YAML")
    parser.add_argument(
        "--mode",
        type=str,
        default="deep_external_state",
        choices=["flat", "deep", "deep_prompt_state", "deep_external_state"],
    )
    parser.add_argument("--model", type=str, default=None)
    parser.add_argument("--mock", action="store_true", help="Use MockLLM")
    args = parser.parse_args()

    persona, _ = load_persona(Path(args.persona))
    cases = DEFAULT_STRESS_CASES.get(persona.persona.id, DEFAULT_STRESS_CASES["evelyn"])

    if args.mock:
        llm = MockLLM(default_response="No way! That never happened, mom. Are you crazy?")
        evaluator = StressTestEvaluator(judge_llm=None)
    else:
        llm = GeminiLLM(model=args.model)
        evaluator = StressTestEvaluator(judge_llm=llm)

    print(f"\n========================================================")
    print(f" Running Adversarial Stress Tests")
    print(f" Persona: {persona.persona.name} ({persona.persona.id})")
    print(f" Mode:    {args.mode}")
    print(f" Cases:   {len(cases)}")
    print(f"========================================================\n")

    results = []
    for idx, case in enumerate(cases, 1):
        agent = PersonaAgent(persona=persona, mode=args.mode, llm=llm)
        response, _, _, _ = agent.respond(case.prompt)

        eval_result = evaluator.evaluate(
            stress_type=case.stress_type,
            persona=persona,
            user_prompt=case.prompt,
            agent_response=response,
        )

        passed = eval_result.get("passed", False)
        status_str = "PASS" if passed else "FAIL"
        print(f"[{status_str}] Test {idx} ({case.stress_type}):")
        print(f"  User Prompt:   {case.prompt}")
        print(f"  Agent Reply:   {response}")
        print(f"  Judge Reason:  {eval_result.get('reasoning', '')}\n")

        results.append({
            "test_type": case.stress_type,
            "prompt": case.prompt,
            "response": response,
            "eval_result": eval_result,
        })

    pass_count = sum(1 for r in results if r["eval_result"].get("passed", False))
    pass_rate = pass_count / len(results) if results else 0.0

    print(f"Stress Test Pass Rate: {pass_rate:.1%} ({pass_count}/{len(results)})\n")

    # Persist results
    out_dir = Path(__file__).resolve().parents[1] / "results" / "stress_tests"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{args.mode}_{persona.persona.id}_stress_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"persona_id": persona.persona.id, "mode": args.mode, "pass_rate": pass_rate, "results": results}, f, indent=2)
    print(f"Saved results to: {out_file}\n")


if __name__ == "__main__":
    main()
