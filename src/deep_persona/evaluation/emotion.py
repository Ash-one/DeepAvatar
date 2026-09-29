"""Emotional expression diversity and intensity evaluation."""

import re
from typing import Any, Dict, List, Optional, Set

# Curated core emotional vocabulary derived from NRC Emotion Lexicon categories
NRC_CORE_EMOTION_WORDS: Set[str] = {
    # Anger / Irritation
    "angry", "mad", "annoyed", "irritated", "furious", "rage", "hate", "resentful", "hostile",
    "spiteful", "bitter", "disgusted", "offensive", "agitated", "defensive",
    # Fear / Anxiety
    "afraid", "scared", "fear", "terrified", "nervous", "anxious", "worried", "panic", "dread",
    "frightened", "vulnerable", "threatened", "horrified", "shaking", "uneasy",
    # Sadness / Guilt
    "sad", "depressed", "miserable", "heartbroken", "grief", "lonely", "isolated", "guilty",
    "ashamed", "hopeless", "hurt", "disappointed", "sorrow", "regret", "exhausted", "burnout",
    # Joy / Relief / Connection
    "happy", "glad", "relieved", "proud", "grateful", "joy", "loved", "excited", "peaceful",
    "content", "comforted", "accepted", "hopeful",
    # Trust / Openness
    "trust", "honest", "sincere", "safe", "understood", "caring", "loyal", "supportive",
}

# Intensity modifier lexicon (degree adverbs and emotional qualifiers)
INTENSITY_MODIFIERS: Set[str] = {
    "deeply", "extremely", "terribly", "immensely", "desperately", "completely",
    "totally", "absolutely", "overwhelmingly", "incredibly", "intensely", "profoundly",
    "really", "very", "so", "barely", "hardly", "slightly", "somewhat", "mildly",
    "partly", "truly", "genuinely", "entirely", "utterly", "drastically", "wildly"
}


class EmotionEvaluator:
    """Evaluates lexical emotion diversity and intensity variation."""

    def __init__(
        self,
        emotion_lexicon: Optional[Set[str]] = None,
        intensity_lexicon: Optional[Set[str]] = None,
        alpha: float = 0.7,
    ):
        self.emotion_lexicon = emotion_lexicon or NRC_CORE_EMOTION_WORDS
        self.intensity_lexicon = intensity_lexicon or INTENSITY_MODIFIERS
        self.alpha = alpha

    def evaluate_conversation(self, turns: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Compute S_emotion across assistant utterances in a conversation.
        """
        all_words: List[str] = []
        found_emotions: Set[str] = set()
        found_intensities: Set[str] = set()

        for turn in turns:
            asst_text = turn.get("assistant", "")
            tokens = re.findall(r"\b[A-Za-z]+\b", asst_text.lower())
            all_words.extend(tokens)
            for token in tokens:
                if token in self.emotion_lexicon:
                    found_emotions.add(token)
                if token in self.intensity_lexicon:
                    found_intensities.add(token)

        total_word_count = len(all_words)
        if total_word_count == 0:
            return {
                "S_emotion": 0.0,
                "D_emotion": 0.0,
                "D_intensity": 0.0,
                "unique_emotion_count": 0,
                "unique_intensity_count": 0,
            }

        # Diversity is normalized by word count (scaled by factor of 100 for percentage readability, then clipped)
        # In literature, diversity is unique_types / total_tokens or density
        d_emotion = len(found_emotions) / total_word_count
        d_intensity = len(found_intensities) / total_word_count

        s_emotion = (self.alpha * d_emotion) + ((1.0 - self.alpha) * d_intensity)

        return {
            "S_emotion": round(s_emotion, 4),
            "D_emotion": round(d_emotion, 4),
            "D_intensity": round(d_intensity, 4),
            "unique_emotion_count": len(found_emotions),
            "unique_intensity_count": len(found_intensities),
            "total_words": total_word_count,
        }
