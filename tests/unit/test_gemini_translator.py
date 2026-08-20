"""
Unit Tests: Gemini LLM Translator Adapter
"""

import pytest

from backend.adapters.translation.gemini_translator import GeminiTranslator
from backend.domain.models import Language


@pytest.mark.asyncio
async def test_gemini_translator_fallback_translation():
    translator = GeminiTranslator(api_key=None)
    res = await translator.translate(
        text="Kal 11 baje meeting rakh lete hain, main demo bhi dikha dunga.",
        source_language=Language.HINGLISH,
        target_language=Language.ENGLISH,
    )
    assert res == "Let's schedule the meeting for 11 tomorrow. I'll also walk you through the demo."


def test_gemini_context_prompt_builder():
    translator = GeminiTranslator(api_key="dummy_key")
    context = [
        {"speaker": "Rajesh", "text": "Are you ready for the demo?"},
        {"speaker": "Sarah", "text": "Yes, please go ahead."},
    ]
    prompt = translator._build_context_prompt(
        text="Haan main demo shuru karta hoon.",
        source_lang=Language.HINGLISH,
        target_lang=Language.ENGLISH,
        context=context,
    )
    assert "Recent conversation context:" in prompt
    assert "Rajesh: Are you ready for the demo?" in prompt
    assert "Haan main demo shuru karta hoon." in prompt
