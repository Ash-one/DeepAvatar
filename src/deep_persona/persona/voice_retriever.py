"""Dynamic Context-Aware Voice Profile Exemplar Retriever."""

from typing import Any, Dict, List, Optional
from deep_persona.memory.store import extract_query_tokens
from deep_persona.persona.schema import PersonaConfig, VoiceExemplar
from deep_persona.runtime.state import PersonaState


class VoiceExemplarRetriever:
    """Retrieves relevant authentic voice exemplars conditioned on conversation context and state."""

    def __init__(self, persona: PersonaConfig):
        self.persona = persona
        self.exemplars: List[VoiceExemplar] = []
        if persona.external_layer.voice_profile and persona.external_layer.voice_profile.exemplars:
            raw_exemplars = persona.external_layer.voice_profile.exemplars
            for item in raw_exemplars:
                if isinstance(item, VoiceExemplar):
                    self.exemplars.append(item)
                elif isinstance(item, dict):
                    try:
                        self.exemplars.append(VoiceExemplar.model_validate(item))
                    except Exception:
                        pass

        # Also automatically index dialogue quotes from Phase A evidence_index
        if hasattr(persona, "evidence_index") and persona.evidence_index:
            for ev in persona.evidence_index:
                if getattr(ev, "type", None) == "dialogue" and ev.observation and ev.observation.speech:
                    speech = ev.observation.speech.strip()
                    if speech and not any(ex.quote == speech for ex in self.exemplars):
                        interlocutor = ev.context.interlocutor if ev.context else None
                        situation = ev.context.situation if ev.context else None
                        self.exemplars.append(
                            VoiceExemplar(
                                quote=speech,
                                context=situation,
                                interlocutor=interlocutor,
                                speech_act="dialogue_utterance",
                            )
                        )

    def retrieve(
        self,
        query: str,
        state: Optional[PersonaState] = None,
        current_interlocutor: Optional[str] = None,
        top_k: int = 3,
    ) -> List[VoiceExemplar]:
        """
        Dynamically rank and select the best few-shot voice exemplars.
        Scoring signals:
        1. Interlocutor match: Does the exemplar's interlocutor match current interlocutor?
        2. Psychological state & tone match:
           - If state is defensive/guarded, prioritize defensive/distressed quotes.
           - If state is open/reflective, prioritize reflective/vulnerable quotes.
        3. Lexical & thematic relevance against query.
        """
        if not self.exemplars:
            return []

        query_tokens = extract_query_tokens(query)
        scored = []

        for ex in self.exemplars:
            score = 0.0

            # 1. Interlocutor match
            if current_interlocutor and ex.interlocutor:
                if (
                    current_interlocutor.lower() in ex.interlocutor.lower()
                    or ex.interlocutor.lower() in current_interlocutor.lower()
                ):
                    score += 5.0

            # 2. Psychological state match
            if state:
                if state.defensiveness >= 0.7 or state.stage in ("defensive", "guarded"):
                    if any(
                        kw in (ex.emotional_tone or "")
                        for kw in ("恐慌", "恐惧", "自嘲", "戒备", "逃避", "痛苦", "苦笑", "畏缩", "fear", "defensive", "sarcastic")
                    ):
                        score += 4.0
                    if any(
                        kw in (ex.speech_act or "")
                        for kw in ("自贬", "掩饰", "防卫", "试探", "deflection", "apology")
                    ):
                        score += 3.0
                elif state.trust >= 0.5 or state.stage in ("open", "reflective"):
                    if any(
                        kw in (ex.emotional_tone or "")
                        for kw in ("坦白", "沉思", "释怀", "真诚", "reflective", "open", "vulnerable")
                    ):
                        score += 4.0

            # 3. Lexical / Topical relevance
            ex_text = f"{ex.quote} {ex.context or ''} {ex.speech_act or ''}".lower()
            for token in query_tokens:
                if token in ex_text:
                    score += len(token) * 0.8

            scored.append((score, ex))

        # Sort descending by score
        scored.sort(key=lambda x: x[0], reverse=True)
        retrieved = [ex for score, ex in scored[:top_k] if score > 0]

        # Fallback to first top_k exemplars if no matches
        if not retrieved:
            retrieved = self.exemplars[:top_k]

        return retrieved
