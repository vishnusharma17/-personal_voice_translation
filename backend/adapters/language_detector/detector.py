"""
Language and Code-Mixing Detector
Identifies Hindi (Devanagari & Latin script Hinglish) and English speech/text.
"""

import re

from backend.domain.interfaces import LanguageDetector
from backend.domain.models import Language


class RuleBasedLanguageDetector(LanguageDetector):
    """
    High-speed, robust language detector with specialized Hinglish support.
    """

    # Common Romanized Hindi / Hinglish markers
    HINGLISH_KEYWORDS = {
        "kya", "kyun", "kaise", "kab", "kahan", "kaun", "mera", "meri", "mere",
        "tera", "teri", "tere", "uska", "uski", "unka", "aap", "aapka", "aapki",
        "tum", "tumhara", "main", "hum", "woh", "yeh", "hain", "hai", "tha",
        "thi", "the", "hoga", "hogi", "honge", "karna", "karo", "karein", "karunga",
        "karungi", "bol", "batao", "suno", "samjhe", "rakh", "lete", "dunga", "degi",
        "dikhana", "dikha", "dikhaunga", "dikhaungi", "chahiye", "aaj", "kal", "parson", "baje",
        "accha", "theek", "bilkul", "bahut", "thoda", "kuch", "sab", "matlab", "shukriya",
        "dhanyawad", "namaste", "bhai", "yaar", "saaf", "aawaz", "sakte", "sakti",
        "ke", "saath", "ka", "ki", "ko", "se", "me", "mein", "par", "raha", "rahi", "rahe",
        "gaya", "gayi", "gaye", "chalo", "chaliye", "karenge", "karta", "karti", "karte",
        "sahi", "badhiya", "kripya", "jaldi", "turant"
    }

    async def detect_language(self, text_or_audio: str | bytes) -> Language:
        if isinstance(text_or_audio, bytes):
            # If raw audio is passed without prior STT, default to AUTO
            return Language.AUTO

        text = text_or_audio.strip()
        if not text:
            return Language.ENGLISH

        # Check for Devanagari Unicode range (\u0900 - \u097F)
        devanagari_chars = len(re.findall(r"[\u0900-\u097F]", text))
        if devanagari_chars > len(text) * 0.2:
            return Language.HINDI

        # Tokenize Latin script words
        words = re.findall(r"\b[a-zA-Z]+\b", text.lower())
        if not words:
            return Language.ENGLISH

        hinglish_matches = sum(1 for w in words if w in self.HINGLISH_KEYWORDS)
        hinglish_ratio = hinglish_matches / len(words)

        if hinglish_ratio >= 0.25 or hinglish_matches > 0 and len(words) <= 4:
            return Language.HINGLISH

        return Language.ENGLISH
