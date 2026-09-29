"""Conversation orchestrator coordinating Agent, User Simulator, and Logger."""

from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from deep_persona.runtime.agent import PersonaAgent
from deep_persona.runtime.logging import ConversationLogger
from deep_persona.simulation.user_agent import UserSimulator


class ConversationRunner:
    """Orchestrates multi-turn dialog flow between PersonaAgent and UserSimulator."""

    def __init__(
        self,
        agent: PersonaAgent,
        user_simulator: Optional[UserSimulator],
        logger: ConversationLogger,
        max_turns: int = 5,
    ):
        self.agent = agent
        self.user_simulator = user_simulator
        self.logger = logger
        self.max_turns = max_turns

    def run(self, initial_opener: Optional[str] = None) -> Tuple[Path, Dict[str, Any]]:
        """
        Execute multi-turn conversation loop.
        Returns:
            Tuple of (saved_file_path, conversation_dict)
        """
        # Get opener
        if initial_opener:
            current_user_msg = initial_opener
        elif self.user_simulator:
            current_user_msg = self.user_simulator.get_preset_opener(seed=self.logger.seed)
        else:
            current_user_msg = "Hello."

        for turn_idx in range(1, self.max_turns + 1):
            # Agent responds
            reply, state_before, state_after, detected_event = self.agent.respond(current_user_msg)

            # Record turn
            self.logger.record_turn(
                turn_index=turn_idx,
                state_before=state_before.to_dict(),
                user_message=current_user_msg,
                assistant_raw=reply,
                state_after=state_after.to_dict(),
                detected_event=detected_event,
            )

            # Prepare next user utterance if not reached max_turns
            if turn_idx < self.max_turns and self.user_simulator:
                current_user_msg = self.user_simulator.step(
                    history=self.agent.history,
                    current_turn=turn_idx + 1,
                )

        saved_path = self.logger.save()
        return saved_path, self.logger.to_dict()
