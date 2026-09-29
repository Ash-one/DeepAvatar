#!/usr/bin/env python3
"""Batch controlled experiment runner across settings A/B/C/D."""

import argparse
from pathlib import Path
import sys
from typing import List

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from deep_persona.llm.gemini import GeminiLLM, MockLLM
from deep_persona.persona.loader import load_persona
from deep_persona.persona.renderer import PromptRenderer
from deep_persona.runtime.agent import PersonaAgent
from deep_persona.runtime.conversation import ConversationRunner
from deep_persona.runtime.logging import ConversationLogger
from deep_persona.simulation.user_agent import UserSimulator


def main():
    parser = argparse.ArgumentParser(description="Run Batch Controlled Experiments.")
    parser.add_argument("--persona", type=str, default="personas/evelyn.yaml", help="Path to persona YAML")
    parser.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3], help="Random seeds list")
    parser.add_argument("--turns", type=int, default=5, help="Number of turns per conversation")
    parser.add_argument(
        "--modes",
        type=str,
        nargs="+",
        default=["flat", "deep", "deep_prompt_state", "deep_external_state"],
        help="List of experimental modes to run",
    )
    parser.add_argument("--model", type=str, default=None)
    parser.add_argument("--mock", action="store_true", help="Use MockLLM")
    args = parser.parse_args()

    persona_path = Path(args.persona)
    persona, persona_hash = load_persona(persona_path)
    renderer = PromptRenderer()

    total_runs = len(args.modes) * len(args.seeds)
    print(f"\n========================================================")
    print(f" Starting Batch Experiment Suite")
    print(f" Persona: {persona.persona.name}")
    print(f" Modes:   {args.modes}")
    print(f" Seeds:   {args.seeds}")
    print(f" Total:   {total_runs} conversations")
    print(f"========================================================\n")

    generated_files: List[Path] = []
    run_idx = 0

    for mode in args.modes:
        template_name = "flat_persona.jinja2" if mode == "flat" else "deep_persona.jinja2"
        prompt_hash = renderer.get_template_hash(template_name)

        for seed in args.seeds:
            run_idx += 1
            print(f"[{run_idx}/{total_runs}] Running Mode={mode} | Seed={seed}...")

            if args.mock:
                agent_llm = MockLLM(default_response="I don't think you understand, mom.")
                user_llm = MockLLM(default_response="Tell me why you're doing this.")
            else:
                agent_llm = GeminiLLM(model=args.model)
                user_llm = GeminiLLM(model=args.model)

            agent = PersonaAgent(
                persona=persona,
                mode=mode,
                llm=agent_llm,
                renderer=renderer,
            )

            user_sim = UserSimulator(
                scenario=persona.scenario,
                llm=user_llm,
                renderer=renderer,
                persona_id=persona.persona.id,
            )

            logger = ConversationLogger(
                experiment_id=mode,
                persona_id=persona.persona.id,
                scenario=persona.scenario.model_dump(),
                model=getattr(agent_llm, "model", "mock"),
                seed=seed,
                hashes={
                    "persona_config_hash": persona_hash,
                    "system_prompt_template_hash": prompt_hash,
                },
            )

            runner = ConversationRunner(
                agent=agent,
                user_simulator=user_sim,
                logger=logger,
                max_turns=args.turns,
            )

            saved_file, _ = runner.run()
            generated_files.append(saved_file)
            print(f"      Saved: {saved_file.name}")

    print(f"\nBatch runs complete. Generated {len(generated_files)} conversation files.")
    print("Now running evaluation across all generated dialogues...\n")

    # Run evaluation script directly
    import subprocess
    cmd = [sys.executable, "scripts/evaluate.py"] + [str(p) for p in generated_files]
    subprocess.run(cmd)


if __name__ == "__main__":
    main()
