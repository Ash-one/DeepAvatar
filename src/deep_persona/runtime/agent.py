"""Persona Agent controlling prompt assembly, state, and response generation."""

from typing import Dict, List, Optional, Tuple
from deep_persona.llm.base import BaseLLM
from deep_persona.memory.store import MemoryStore
from deep_persona.persona.renderer import PromptRenderer
from deep_persona.persona.schema import PersonaConfig
from deep_persona.persona.voice_retriever import VoiceExemplarRetriever
from deep_persona.runtime.state import PersonaState
from deep_persona.runtime.transitions import StateManager, classify_event_rule_based


class PersonaAgent:
    """Agent representing a simulated persona across different experimental modes."""

    def __init__(
        self,
        persona: PersonaConfig,
        mode: str = "deep_external_state",
        llm: Optional[BaseLLM] = None,
        renderer: Optional[PromptRenderer] = None,
        initial_state: Optional[PersonaState] = None,
        memory_store: Optional[MemoryStore] = None,
        voice_retriever: Optional[VoiceExemplarRetriever] = None,
        temperature: float = 0.7,
        top_p: float = 0.95,
        max_tokens: int = 1024,
    ):
        self.persona = persona
        self.mode = mode
        self.llm = llm
        self.renderer = renderer or PromptRenderer()
        self.memory_store = memory_store or MemoryStore(persona=persona)
        self.voice_retriever = voice_retriever or VoiceExemplarRetriever(persona=persona)
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens

        # External state manager for external state mode
        self.state_manager = StateManager(persona, initial_state=initial_state)
        # For prompt state or deep/flat, keep a baseline state tracker
        self.current_state = initial_state or PersonaState.create_for_persona(persona)
        self.history: List[Dict[str, str]] = []

    def respond(self, user_message: str) -> Tuple[str, PersonaState, PersonaState, str]:
        """
        Process user message and generate agent reply.
        Returns:
            Tuple of (agent_reply, state_before_snapshot, state_after_snapshot, detected_event)
        """
        # Snapshot state before turn
        state_before = PersonaState.from_dict(self.current_state.to_dict())

        # Determine event
        detected_event = classify_event_rule_based(
            user_message,
            self.state_manager.history_events if self.mode == "deep_external_state" else None,
        )

        if self.mode == "deep_external_state":
            # Mode B: Advance deterministic state machine
            self.current_state = self.state_manager.update(user_message, detected_event=detected_event)
        elif self.mode == "deep_prompt_state":
            # Update turn counter
            self.current_state.turn += 1
        elif self.mode in ("deep", "flat"):
            self.current_state.turn += 1

        state_after = PersonaState.from_dict(self.current_state.to_dict())

        # Retrieve perspective-bounded memory context and context-aware voice exemplars if applicable
        memory_context = None
        voice_exemplars = None
        if self.mode != "flat":
            current_user_role = self.persona.scenario.user_role if self.persona.scenario else None
            memory_context = self.memory_store.retrieve(
                query=user_message,
                current_interlocutor=current_user_role,
            )
            voice_exemplars = self.voice_retriever.retrieve(
                query=user_message,
                state=self.current_state,
                current_interlocutor=current_user_role,
                top_k=3,
            )

        # Render system prompt
        system_prompt = self.renderer.render_persona(
            persona=self.persona,
            mode=self.mode,
            state=self.current_state,
            memory_context=memory_context,
            voice_exemplars=voice_exemplars,
        )

        # Build messages payload
        messages = list(self.history)
        messages.append({"role": "user", "content": user_message})

        if self.llm is None:
            raise RuntimeError("LLM client not configured for PersonaAgent")

        response = self.llm.generate(
            messages=messages,
            system_prompt=system_prompt,
            temperature=self.temperature,
            top_p=self.top_p,
            max_tokens=self.max_tokens,
        )

        reply_content = response.content
        # Update history
        self.history.append({"role": "user", "content": user_message})
        self.history.append({"role": "assistant", "content": reply_content})

        return reply_content, state_before, state_after, detected_event
