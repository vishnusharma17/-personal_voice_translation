"""
Unit Tests: Language and Hinglish Detection
"""

import pytest
from backend.adapters.language_detector.detector import RuleBasedLanguageDetector
from backend.domain.models import Language


@pytest.mark.asyncio
async def test_detect_hinglish_colloquial():
    detector = RuleBasedLanguageDetector()
    lang = await detector.detect_language("Kal 11 baje meeting rakh lete hain, main demo bhi dikha dunga.")
    assert lang == Language.HINGLISH


@pytest.mark.asyncio
async def test_detect_devanagari_hindi():
    detector = RuleBasedLanguageDetector()
    lang = await detector.detect_language("नमस्ते, आप कैसे हैं?")
    assert lang == Language.HINDI


@pytest.mark.asyncio
async def test_detect_english():
    detector = RuleBasedLanguageDetector()
    lang = await detector.detect_language("Let's schedule the meeting for tomorrow morning.")
    assert lang == Language.ENGLISH


@pytest.mark.asyncio
async def test_detect_short_hinglish_question():
    detector = RuleBasedLanguageDetector()
    lang = await detector.detect_language("kya haal hai?")
    assert lang == Language.HINGLISH
