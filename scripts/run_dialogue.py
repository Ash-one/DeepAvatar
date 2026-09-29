#!/usr/bin/env python3
"""Run single multi-turn dialogue with PersonaAgent."""

import argparse
from pathlib import Path
import sys

# Ensure src in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from deep_persona.llm.gemini import GeminiLLM, MockLLM
from deep_persona.persona.loader import load_persona
from deep_persona.persona.renderer import PromptRenderer
from deep_persona.runtime.agent import PersonaAgent
from deep_persona.runtime.conversation import ConversationRunner
from deep_persona.runtime.logging import ConversationLogger
from deep_persona.simulation.user_agent import UserSimulator


def main():
    parser = argparse.ArgumentParser(description="Run Deep Persona dialogue simulation.")
    parser.add_argument("--persona", type=str, default="personas/toy_persona.yaml", help="Path to persona YAML")
    parser.add_argument(
        "--mode",
        type=str,
        default="deep_external_state",
        choices=["flat", "deep", "deep_prompt_state", "deep_external_state"],
        help="Experiment setting mode",
    )
    parser.add_argument("--turns", type=int, default=5, help="Number of dialogue turns")
    parser.add_argument("--model", type=str, default=None, help="LLM model name")
    parser.add_argument("--seed", type=int, default=42, help="Seed index for opener and consistency")
    parser.add_argument("--mock", action="store_true", help="Use deterministic MockLLM instead of API")
    parser.add_argument("--interactive", action="store_true", help="Interactive terminal user mode")
    args = parser.parse_args()

    # Load persona
    persona_path = Path(args.persona)
    persona, persona_hash = load_persona(persona_path)

    # Setup LLM
    if args.mock:
        agent_llm = MockLLM(default_response="I'm sorry, I didn't mean to do that.")
        user_llm = MockLLM(default_response="Can you tell me how it happened?")
    else:
        agent_llm = GeminiLLM(model=args.model)
        user_llm = GeminiLLM(model=args.model)

    renderer = PromptRenderer()
    template_name = "flat_persona.jinja2" if args.mode == "flat" else "deep_persona.jinja2"
    prompt_hash = renderer.get_template_hash(template_name)

    # Initialize agent
    agent = PersonaAgent(
        persona=persona,
        mode=args.mode,
        llm=agent_llm,
        renderer=renderer,
    )

    # Initialize user simulator if not interactive
    user_sim = None
    if not args.interactive:
        user_sim = UserSimulator(
            scenario=persona.scenario,
            llm=user_llm,
            renderer=renderer,
            persona_id=persona.persona.id,
        )

    # Initialize logger
    logger = ConversationLogger(
        experiment_id=args.mode,
        persona_id=persona.persona.id,
        scenario=persona.scenario.model_dump(),
        model=getattr(agent_llm, "model", "mock"),
        seed=args.seed,
        hashes={
            "persona_config_hash": persona_hash,
            "system_prompt_template_hash": prompt_hash,
        },
    )

    print(f"\n========================================================")
    print(f" Starting Dialogue Simulation")
    print(f" Persona: {persona.persona.name} ({persona.persona.id})")
    print(f" Mode:    {args.mode}")
    print(f" Model:   {getattr(agent_llm, 'model', 'mock')}")
    print(f" Turns:   {args.turns}")
    print(f"========================================================\n")

    if args.interactive:
        print(f"Scenario Context: {persona.scenario.initial_context}\n")
        for turn_idx in range(1, args.turns + 1):
            user_msg = input(f"Turn {turn_idx} [You - {persona.scenario.user_role}]: ")
            reply, state_before, state_after, event = agent.respond(user_msg)
            logger.record_turn(
                turn_index=turn_idx,
                state_before=state_before.to_dict(),
                user_message=user_msg,
                assistant_raw=reply,
                state_after=state_after.to_dict(),
                detected_event=event,
            )
            print(f"Turn {turn_idx} [{persona.persona.name} ({args.mode})]: {reply}\n")
        saved_file = logger.save()
    else:
        runner = ConversationRunner(
            agent=agent,
            user_simulator=user_sim,
            logger=logger,
            max_turns=args.turns,
        )
        saved_file, conv_dict = runner.run()
        for turn in conv_dict["turns"]:
            print(f"Turn {turn['turn']} [{persona.scenario.user_role}]: {turn['user']}")
            asst_text = turn["assistant"]
            if turn["assistant_embodied_action"]:
                asst_text += f" {turn['assistant_embodied_action']}"
            print(f"Turn {turn['turn']} [{persona.persona.name}]: {asst_text}")
            if args.mode == "deep_external_state":
                st = turn["state_after"]
                print(f"  --> State: stage={st['stage']}, trust={st['trust']}, def={st['defensiveness']}, revealed={st['revealed_information']}")
            print()

    print(f"Successfully finished dialogue.")
    print(f"Saved conversation trajectory to: {saved_file}\n")


if __name__ == "__main__":
    main()
