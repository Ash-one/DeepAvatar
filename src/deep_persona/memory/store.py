"""Memory store and perspective-bounded retrieval engine."""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

from deep_persona.memory.schema import (
    EpisodicMemory,
    MemoryConfig,
    PerspectiveBoundary,
    RelationshipMemory,
    SemanticMemory,
)


def extract_query_tokens(text: str) -> List[str]:
    """Extract lexical keywords and Chinese character shingles (2-4 grams) for retrieval matching."""
    tokens = set()
    # English and alphanumeric words
    words = re.findall(r"[a-zA-Z0-9_]+", text.lower())
    for w in words:
        if len(w) >= 2:
            tokens.add(w)

    # Chinese n-grams (2-gram and 3-gram shingles)
    c_chars = re.sub(r"[^\u4e00-\u9fff]", "", text)
    if c_chars:
        # Stopwords to exclude in Chinese matching
        stopwords = {"什么", "怎么", "如何", "我们", "你们", "他们", "可以", "这个", "那个", "一下", "是不是", "有没有", "听说"}
        for n in (2, 3):
            for i in range(len(c_chars) - n + 1):
                gram = c_chars[i : i + n]
                if gram not in stopwords:
                    tokens.add(gram)

    return list(tokens)


class MemoryStore:
    """Manages multi-tier memories and perspective boundaries for a persona."""

    def __init__(
        self,
        memory_config: Optional[MemoryConfig] = None,
        persona: Optional[Any] = None,
    ):
        self.config = memory_config or MemoryConfig()
        if persona:
            self._load_from_persona(persona)

    def _load_from_persona(self, persona: Any) -> None:
        mem = getattr(persona, "memory", None)
        if mem is not None:
            if isinstance(mem, MemoryConfig):
                self.config = mem
            elif isinstance(mem, dict):
                self.config = MemoryConfig.model_validate(mem)
            return

        # Attempt to load from personas/memories/<persona_id>.yaml if exists
        p_id = getattr(getattr(persona, "persona", None), "id", None) or getattr(persona, "id", None)
        if p_id:
            memory_file = Path("personas") / "memories" / f"{p_id}.yaml"
            if memory_file.exists():
                try:
                    with open(memory_file, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                        if isinstance(data, dict):
                            self.config = MemoryConfig.model_validate(data)
                except Exception:
                    pass

    def retrieve(
        self,
        query: str,
        current_interlocutor: Optional[str] = None,
        top_k: int = 3,
    ) -> Dict[str, Any]:
        """
        Retrieve relevant episodic memories, matching relationship memory,
        and authoritative perspective boundaries based on query and context.
        """
        query_tokens = extract_query_tokens(query)
        scored_episodes = []

        for ep in self.config.episodic_memories:
            score = 0
            ep_text = f"{ep.summary} {ep.details} {' '.join(ep.participants)}".lower()
            for token in query_tokens:
                if token in ep_text:
                    score += len(token)  # longer match yields higher relevance

            if current_interlocutor and any(current_interlocutor.lower() in p.lower() for p in ep.participants):
                score += 3

            scored_episodes.append((score, ep))

        scored_episodes.sort(key=lambda x: (x[0], x[1].timestamp_order), reverse=True)
        retrieved_episodes = [ep for score, ep in scored_episodes[:top_k] if score > 0]

        if not retrieved_episodes and self.config.episodic_memories:
            retrieved_episodes = self.config.episodic_memories[:top_k]

        matched_relationship: Optional[RelationshipMemory] = None
        if current_interlocutor:
            target_norm = current_interlocutor.lower()
            for rel in self.config.relationship_memories:
                if (
                    rel.target_character.lower() in target_norm
                    or rel.relation.lower() in target_norm
                    or target_norm in rel.target_character.lower()
                ):
                    matched_relationship = rel
                    break

        matched_semantics: List[SemanticMemory] = []
        for sem in self.config.semantic_memories:
            if sem.concept.lower() in query.lower():
                matched_semantics.append(sem)

        return {
            "epistemic_horizon": self.config.epistemic_horizon,
            "perspective_boundary": self.config.perspective_boundary,
            "episodic_memories": retrieved_episodes,
            "relationship_memory": matched_relationship,
            "semantic_memories": matched_semantics,
        }
