"""
Unit Tests: Translation Adapter
"""

import pytest
from backend.adapters.translation.mock_translator import MockTranslator
from backend.domain.models import Language


@pytest.mark.asyncio
async def test_hinglish_to_english_conversational_translation():
    translator = MockTranslator()
    input_text = "Kal 11 baje meeting rakh lete hain, main demo bhi dikha dunga."
    translated = await translator.translate(
        text=input_text,
        source_language=Language.HINGLISH,
        target_language=Language.ENGLISH,
    )
    assert translated == "Let's schedule the meeting for 11 tomorrow. I'll also walk you through the demo."


@pytest.mark.asyncio
async def test_english_to_hindi_reverse_translation():
    translator = MockTranslator()
    input_text = "Let's schedule the meeting for 11 tomorrow. I'll also walk you through the demo."
    translated = await translator.translate(
        text=input_text,
        source_language=Language.ENGLISH,
        target_language=Language.HINDI,
    )
    assert "कल 11 बजे" in translated


@pytest.mark.asyncio
async def test_streaming_translation():
    translator = MockTranslator()
    
    async def sample_stream():
        yield "kya aap meri aawaz "
        yield "sun sakte hain?"

    collected = []
    async for chunk in translator.translate_stream(
        text_stream=sample_stream(),
        source_language=Language.HINGLISH,
        target_language=Language.ENGLISH,
    ):
        collected.append(chunk)

    full = "".join(collected)
    assert "Can you hear" in full
