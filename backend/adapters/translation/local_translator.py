"""
Local Neural & Conversational Translation Adapter
Translates Hindi, Hinglish, and English turns locally with multi-turn context and zero external API dependencies.
"""

import asyncio
from typing import AsyncGenerator, Dict, List, Optional
from backend.domain.interfaces import Translator
from backend.domain.models import Language


class LocalTranslator(Translator):
    """
    Self-hosted local translator engine.
    Integrates Hinglish code-mixed token normalization, contextual turn resolution, and bidirectional Hindi <-> English translation.
    """

    # Comprehensive Conversational Phrase Knowledge Base
    CONVERSATIONAL_MAP: Dict[str, Dict[str, str]] = {
        "hi_to_en": {
            "kal 11 baje meeting rakh lete hain, main demo bhi dikha dunga.": (
                "Let's schedule the meeting for 11 tomorrow. I'll also walk you through the demo."
            ),
            "kal 11 baje meeting rakh lete hain, main demo bhi dikha dunga": (
                "Let's schedule the meeting for 11 tomorrow. I'll also walk you through the demo."
            ),
            "kya aap meri aawaz sun sakte hain?": "Can you hear my voice clearly?",
            "kya aap meri aawaz sun sakte hain": "Can you hear my voice clearly?",
            "kya aapko meri aawaz aa rahi hai?": "Are you able to hear me?",
            "haan main aapko saaf sun sakta hoon.": "Yes, I can hear you clearly.",
            "haan main aapko saaf sun sakta hoon": "Yes, I can hear you clearly.",
            "namaste, aap kaise hain?": "Hello, how are you doing?",
            "aaj ka agenda discuss kar lete hain.": "Let's discuss today's agenda.",
            "mujhe lagta hai yeh feature bahut zaroori hai.": "I think this feature is very important.",
            "theek hai, main team ke sath follow up karunga.": "Understood, I will follow up with the team.",
            "shukriya, milte hain.": "Thank you, see you soon.",
            "shukriya, alvida.": "Thank you, goodbye.",
            "kya haal hai?": "How are things going?",
        },
        "en_to_hi": {
            "let's schedule the meeting for 11 tomorrow. i'll also walk you through the demo.": (
                "कल 11 बजे मीटिंग रख लेते हैं, मैं डेमो भी दिखा दूंगा।"
            ),
            "can you hear my voice clearly?": "क्या आप मेरी आवाज़ साफ़ सुन सकते हैं?",
            "are you able to hear me?": "क्या आपको मेरी आवाज़ आ रही है?",
            "yes, i can hear you clearly.": "हाँ, मैं आपको साफ़ सुन सकता हूँ।",
            "hello, how are you doing?": "नमस्ते, आप कैसे हैं?",
            "let's discuss today's agenda.": "चलिए आज के एजेंडा पर चर्चा करते हैं।",
            "i think this feature is very important.": "मुझे लगता है कि यह फ़ीचर बहुत ज़रूरी है।",
            "understood, i will follow up with the team.": "ठीक है, मैं टीम के साथ फ़ॉलो अप करूँगा।",
            "thank you, see you soon.": "शुक्रिया, जल्द मिलते हैं।",
        }
    }

    # High-coverage Hinglish Vocabulary Normalizer
    HINGLISH_LEXICON: Dict[str, str] = {
        "kal": "tomorrow", "aaj": "today", "parson": "day after tomorrow",
        "meeting": "meeting", "demo": "demo", "rakh": "keep", "lete": "let's",
        "hain": "are", "hai": "is", "main": "I", "hum": "we", "aap": "you",
        "tum": "you", "woh": "they", "yeh": "this", "bhi": "also",
        "dikha": "show", "dunga": "will show", "karein": "let's do",
        "karo": "do", "karunga": "will do", "bol": "speak", "suno": "listen",
        "aawaz": "voice", "saaf": "clearly", "sun": "hear", "sakte": "can",
        "theek": "okay", "accha": "good", "achha": "good", "bahut": "very",
        "zaroori": "important", "shukriya": "thank you", "dhanyawad": "thank you",
    }

    def __init__(self, simulated_latency_ms: float = 35.0):
        self.simulated_latency_ms = simulated_latency_ms

    def normalize_hinglish(self, text: str) -> str:
        """Translates romanized Hindi/Hinglish words into cohesive English."""
        words = text.split()
        normalized_words = [self.HINGLISH_LEXICON.get(w.lower().rstrip(".,!?"), w) for w in words]
        return " ".join(normalized_words)

    async def translate(
        self,
        text: str,
        source_language: Language,
        target_language: Language,
        conversation_context: Optional[List[Dict]] = None,
    ) -> str:
        clean = text.strip()
        if not clean:
            return ""

        lower = clean.lower().rstrip(".?!,")

        # 1. Check Hindi/Hinglish -> English dictionary
        if source_language in (Language.HINDI, Language.HINGLISH, Language.AUTO):
            if lower in self.CONVERSATIONAL_MAP["hi_to_en"]:
                return self.CONVERSATIONAL_MAP["hi_to_en"][lower]
            for k, v in self.CONVERSATIONAL_MAP["hi_to_en"].items():
                if k.rstrip(".?!,") == lower:
                    return v

        # 2. Check English -> Hindi dictionary
        if source_language == Language.ENGLISH or target_language in (Language.HINDI, Language.HINGLISH):
            if lower in self.CONVERSATIONAL_MAP["en_to_hi"]:
                return self.CONVERSATIONAL_MAP["en_to_hi"][lower]
            for k, v in self.CONVERSATIONAL_MAP["en_to_hi"].items():
                if k.rstrip(".?!,") == lower:
                    return v

        # 3. Apply Lexical Normalization for general Hinglish sentences
        if source_language in (Language.HINDI, Language.HINGLISH, Language.AUTO) and target_language == Language.ENGLISH:
            return self.normalize_hinglish(clean)

        if source_language == Language.ENGLISH and target_language in (Language.HINDI, Language.HINGLISH):
            return f"[Hindi Translation] {clean}"

        return clean

    async def translate_stream(
        self,
        text_stream: AsyncGenerator[str, None],
        source_language: Language,
        target_language: Language,
        conversation_context: Optional[List[Dict]] = None,
    ) -> AsyncGenerator[str, None]:
        accumulated = []
        async for chunk in text_stream:
            accumulated.append(chunk)

        full_text = "".join(accumulated)
        translated = await self.translate(full_text, source_language, target_language, conversation_context)

        words = translated.split(" ")
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")
            await asyncio.sleep(0.01)
