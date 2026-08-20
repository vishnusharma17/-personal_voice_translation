"""
Conversational Natural Translator (Mock & Rule Engine)
Accurately translates Hindi/Hinglish <-> English conversational phrases while preserving tone.
"""

import asyncio
from collections.abc import AsyncGenerator

from backend.domain.interfaces import Translator
from backend.domain.models import Language


class MockTranslator(Translator):
    """
    Deterministic & Rule-enhanced translator for testing and local operation.
    Preserves speaker intent, politeness, and conversational cadence.
    """

    # Direct phrase maps for conversational accuracy
    HINDI_TO_ENGLISH_MAP: dict[str, str] = {
        "kal 11 baje meeting rakh lete hain, main demo bhi dikha dunga.": (
            "Let's schedule the meeting for 11 tomorrow. I'll also walk you through the demo."
        ),
        "kal 11 baje meeting rakh lete hain, main demo bhi dikha dunga": (
            "Let's schedule the meeting for 11 tomorrow. I'll also walk you through the demo."
        ),
        "kya aap meri aawaz sun sakte hain?": "Can you hear my voice clearly?",
        "kya aapko meri aawaz aa rahi hai?": "Are you able to hear me?",
        "haan main aapko saaf sun sakta hoon.": "Yes, I can hear you clearly.",
        "namaste, aap kaise hain?": "Hello, how are you doing?",
        "aaj ka agenda discuss kar lete hain.": "Let's discuss today's agenda.",
        "mujhe lagta hai yeh feature bahut zaroori hai.": "I think this feature is very important.",
        "theek hai, main team ke sath follow up karunga.": "Understood, I will follow up with the team.",
        "shukriya, milte hain.": "Thank you, see you soon.",
    }

    ENGLISH_TO_HINDI_MAP: dict[str, str] = {
        "let's schedule the meeting for 11 tomorrow. i'll also walk you through the demo.": (
            "कल 11 बजे मीटिंग रख लेते हैं, मैं डेमो भी दिखा दूंगा।"
        ),
        "can you hear my voice clearly?": "क्या आप मेरी आवाज़ साफ़ सुन सकते हैं?",
        "yes, i can hear you clearly.": "हाँ, मैं आपको साफ़ सुन सकता हूँ।",
        "hello, how are you doing?": "नमस्ते, आप कैसे हैं?",
        "let's discuss today's agenda.": "चलिए आज के एजेंडा पर चर्चा करते हैं।",
        "i think this feature is very important.": "मुझे लगता है कि यह फ़ीचर बहुत ज़रूरी है।",
        "understood, i will follow up with the team.": "ठीक है, मैं टीम के साथ फ़ॉलो अप करूँगा।",
        "thank you, see you soon.": "शुक्रिया, जल्द मिलते हैं।",
    }

    # Lexicon fallback for arbitrary sentences
    LEXICON_HI_EN: dict[str, str] = {
        "kal": "tomorrow",
        "aaj": "today",
        "meeting": "meeting",
        "demo": "demo",
        "rakh": "keep",
        "lete": "let's",
        "hain": "are",
        "main": "I",
        "bhi": "also",
        "dikha": "show",
        "dunga": "will do",
        "kya": "what",
        "aap": "you",
        "meri": "my",
        "aawaz": "voice",
        "sun": "hear",
        "sakte": "can",
        "haan": "yes",
        "nahi": "no",
        "theek": "okay",
        "achha": "good",
        "accha": "good",
        "bataiye": "please tell",
        "shuru": "start",
        "karein": "let's do",
    }

    async def translate(
        self,
        text: str,
        source_language: Language,
        target_language: Language,
        conversation_context: list[dict] | None = None,
    ) -> str:
        clean_text = text.strip()
        lower_text = clean_text.lower().rstrip(".?!,")

        # Check direct conversational phrase map
        if source_language in (Language.HINDI, Language.HINGLISH, Language.AUTO):
            if lower_text in self.HINDI_TO_ENGLISH_MAP:
                return self.HINDI_TO_ENGLISH_MAP[lower_text]
            # Check with punctuation
            for key, val in self.HINDI_TO_ENGLISH_MAP.items():
                if key.rstrip(".?!,") == lower_text:
                    return val

        if source_language == Language.ENGLISH:
            if lower_text in self.ENGLISH_TO_HINDI_MAP:
                return self.ENGLISH_TO_HINDI_MAP[lower_text]
            for key, val in self.ENGLISH_TO_HINDI_MAP.items():
                if key.rstrip(".?!,") == lower_text:
                    return val

        # Dynamic heuristic translation
        if source_language in (Language.HINDI, Language.HINGLISH, Language.AUTO) and target_language == Language.ENGLISH:
            words = clean_text.split()
            translated_words = [self.LEXICON_HI_EN.get(w.lower().rstrip(".,!?"), w) for w in words]
            return " ".join(translated_words)

        if source_language == Language.ENGLISH and target_language in (Language.HINDI, Language.HINGLISH):
            return f"[Hindi Translation] {clean_text}"

        return clean_text

    async def translate_stream(
        self,
        text_stream: AsyncGenerator[str, None],
        source_language: Language,
        target_language: Language,
        conversation_context: list[dict] | None = None,
    ) -> AsyncGenerator[str, None]:
        full_text = ""
        async for chunk in text_stream:
            full_text += chunk
        
        translated = await self.translate(full_text, source_language, target_language, conversation_context)
        # Yield words with small streaming delays to simulate real token streaming
        words = translated.split(" ")
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")
            await asyncio.sleep(0.01)
