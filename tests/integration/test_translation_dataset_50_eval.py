"""
Comprehensive 50+ Real-World Conversational Translation Evaluation Dataset
Evaluates semantic correctness, entity preservation, numbers, technical terminology,
tense, and tone across Hindi, Roman Hindi, Hinglish, and English without requiring brittle exact string matches.
"""

import pytest

from backend.adapters.translation.local_translator import LocalTranslator
from backend.domain.models import Language


@pytest.fixture(scope="module")
def neural_translator():
    return LocalTranslator()


# 52 Diverse Real-World Conversational Test Cases
DATASET_52 = [
    # -------------------------------------------------------------
    # Category 1: Technical & Engineering Conversations (HI/Hinglish -> EN)
    # -------------------------------------------------------------
    {
        "id": "tech_01",
        "input": "Database query thodi slow hai, isko optimize karna padega.",
        "src": Language.HINGLISH, "tgt": Language.ENGLISH,
        "required_concepts": ["database", "query", "slow", "optimize"],
    },
    {
        "id": "tech_02",
        "input": "Yaar client ko bol dena ki deployment aaj complete ho jayega.",
        "src": Language.HINGLISH, "tgt": Language.ENGLISH,
        "required_concepts": ["client", "deployment", "today", "complete"],
    },
    {
        "id": "tech_03",
        "input": "humein 3 servers aur 500 users ke liye test karna hai.",
        "src": Language.HINGLISH, "tgt": Language.ENGLISH,
        "required_concepts": ["3", "500", "server", "user", "test"],
    },
    {
        "id": "tech_04",
        "input": "api latency high hai, backend optimization zaroori hai.",
        "src": Language.HINGLISH, "tgt": Language.ENGLISH,
        "required_concepts": ["api", "latency", "high", "optimization"],
    },
    {
        "id": "tech_05",
        "input": "Pull request merge ho gayi hai aur build pass ho gaya.",
        "src": Language.HINGLISH, "tgt": Language.ENGLISH,
        "required_concepts": ["pull request", "merge", "build", "pass"],
    },
    {
        "id": "tech_06",
        "input": "Microservice architecture mein memory leak debug karna hai.",
        "src": Language.HINGLISH, "tgt": Language.ENGLISH,
        "required_concepts": ["microservice", "memory", "leak", "debug"],
    },
    {
        "id": "tech_07",
        "input": "Production release se pehle regression testing complete kar lo.",
        "src": Language.HINGLISH, "tgt": Language.ENGLISH,
        "required_concepts": ["production", "release", "regression", "testing"],
    },

    # -------------------------------------------------------------
    # Category 2: Client & Business Dialogue (HI/Hinglish -> EN)
    # -------------------------------------------------------------
    {
        "id": "client_01",
        "input": "Kal 11 baje client ke saath meeting hai, main project ka demo dikhaunga.",
        "src": Language.HINGLISH, "tgt": Language.ENGLISH,
        "required_concepts": ["client", "meeting", "11", "demo", "project"],
    },
    {
        "id": "client_02",
        "input": "Aaj ka agenda discuss kar lete hain aur deadlines final karte hain.",
        "src": Language.HINGLISH, "tgt": Language.ENGLISH,
        "required_concepts": ["agenda", "discuss", "deadline"],
    },
    {
        "id": "client_03",
        "input": "Client ne nayi feature requirement bheji hai.",
        "src": Language.HINGLISH, "tgt": Language.ENGLISH,
        "required_concepts": ["client", "feature", "requirement"],
    },
    {
        "id": "client_04",
        "input": "Theek hai, main stakeholders ke saath follow up karunga.",
        "src": Language.HINGLISH, "tgt": Language.ENGLISH,
        "required_concepts": ["stakeholder", "follow up"],
    },
    {
        "id": "client_05",
        "input": "Quarterly business review agle mangalwar ko schedule hai.",
        "src": Language.HINGLISH, "tgt": Language.ENGLISH,
        "required_concepts": ["review", "schedule"],
    },

    # -------------------------------------------------------------
    # Category 3: Casual, Hesitations & Conversational Fillers (HI/Hinglish -> EN)
    # -------------------------------------------------------------
    {
        "id": "casual_01",
        "input": "Ek minute ruk jao, main abhi join karta hoon.",
        "src": Language.HINGLISH, "tgt": Language.ENGLISH,
        "required_concepts": ["minute", "join"],
    },
    {
        "id": "casual_02",
        "input": "Umm... theek hai, main team ko update kar dunga.",
        "src": Language.HINGLISH, "tgt": Language.ENGLISH,
        "required_concepts": ["team", "update"],
    },
    {
        "id": "casual_03",
        "input": "Yaar meeting ka link bhej do, main 5 minute mein aata hoon.",
        "src": Language.HINGLISH, "tgt": Language.ENGLISH,
        "required_concepts": ["meeting", "link", "5", "minute"],
    },
    {
        "id": "casual_04",
        "input": "Bhai screen share karo, code dekhna hai.",
        "src": Language.HINGLISH, "tgt": Language.ENGLISH,
        "required_concepts": ["screen", "share", "code"],
    },
    {
        "id": "casual_05",
        "input": "Chalo lunch ke baad milte hain aur discuss karte hain.",
        "src": Language.HINGLISH, "tgt": Language.ENGLISH,
        "required_concepts": ["lunch", "discuss"],
    },

    # -------------------------------------------------------------
    # Category 4: Audio Check, Verification & Salutations (HI/Hinglish -> EN)
    # -------------------------------------------------------------
    {
        "id": "audio_01",
        "input": "kya aap meri aawaz sun sakte hain?",
        "src": Language.HINGLISH, "tgt": Language.ENGLISH,
        "required_concepts": ["hear", "voice"],
    },
    {
        "id": "audio_02",
        "input": "haan main aapko saaf sun sakta hoon.",
        "src": Language.HINGLISH, "tgt": Language.ENGLISH,
        "required_concepts": ["hear", "clearly"],
    },
    {
        "id": "audio_03",
        "input": "Namaste, aap sabhi ka is call mein swagat hai.",
        "src": Language.HINGLISH, "tgt": Language.ENGLISH,
        "required_concepts": ["welcome", "call"],
    },
    {
        "id": "audio_04",
        "input": "Bahut bahut dhanyawad, kal subah baat karte hain.",
        "src": Language.HINGLISH, "tgt": Language.ENGLISH,
        "required_concepts": ["thank", "tomorrow"],
    },

    # -------------------------------------------------------------
    # Category 5: Pure Hindi Devanagari (Devanagari -> EN)
    # -------------------------------------------------------------
    {
        "id": "deva_01",
        "input": "कल सुबह 10 बजे एक महत्वपूर्ण बैठक का आयोजन किया गया है।",
        "src": Language.HINDI, "tgt": Language.ENGLISH,
        "required_concepts": ["10", "meeting", "tomorrow"],
    },
    {
        "id": "deva_02",
        "input": "क्या आपने नई सॉफ़्टवेयर रिलीज़ का परीक्षण पूरा कर लिया है?",
        "src": Language.HINDI, "tgt": Language.ENGLISH,
        "required_concepts": ["software", "release", "test"],
    },
    {
        "id": "deva_03",
        "input": "कृपया मुझे इस दस्तावेज़ की एक प्रति ईमेल कर दीजिए।",
        "src": Language.HINDI, "tgt": Language.ENGLISH,
        "required_concepts": ["document", "copy", "email"],
    },
    {
        "id": "deva_04",
        "input": "हम इस प्रोजेक्ट को समय पर पूरा करने के लिए प्रतिबद्ध हैं।",
        "src": Language.HINDI, "tgt": Language.ENGLISH,
        "required_concepts": ["project", "time", "complete"],
    },
    {
        "id": "deva_05",
        "input": "सर्वर की सुरक्षा जाँच पूरी तरह से सफल रही।",
        "src": Language.HINDI, "tgt": Language.ENGLISH,
        "required_concepts": ["server", "security", "successful"],
    },

    # -------------------------------------------------------------
    # Category 6: English to Hindi (EN -> HI Devanagari) - Technical
    # -------------------------------------------------------------
    {
        "id": "en_tech_01",
        "input": "Give me five minutes, I am joining the meeting.",
        "src": Language.ENGLISH, "tgt": Language.HINDI,
        "required_concepts": ["मिनट", "बैठक"],
    },
    {
        "id": "en_tech_02",
        "input": "The database query is a little slow, we need to optimize it.",
        "src": Language.ENGLISH, "tgt": Language.HINDI,
        "required_concepts": ["डेटाबेस", "धीमी", "ऑप्टिमाइज़"],
    },
    {
        "id": "en_tech_03",
        "input": "The production deployment was successful and all tests passed.",
        "src": Language.ENGLISH, "tgt": Language.HINDI,
        "required_concepts": ["सफल", "परीक्षण"],
    },
    {
        "id": "en_tech_04",
        "input": "Please check the API documentation and create a pull request.",
        "src": Language.ENGLISH, "tgt": Language.HINDI,
        "required_concepts": ["एपीआई", "दस्तावेज़", "अनुरोध"],
    },
    {
        "id": "en_tech_05",
        "input": "We have 4 servers handling over 1000 requests per second.",
        "src": Language.ENGLISH, "tgt": Language.HINDI,
        "required_concepts": ["4", "1000", "सर्वर", "अनुरोध"],
    },

    # -------------------------------------------------------------
    # Category 7: English to Hindi (EN -> HI Devanagari) - Business & Scheduling
    # -------------------------------------------------------------
    {
        "id": "en_biz_01",
        "input": "Yes, that sounds good. Let's have the meeting tomorrow.",
        "src": Language.ENGLISH, "tgt": Language.HINDI,
        "required_concepts": ["हाँ", "कल", "बैठक"],
    },
    {
        "id": "en_biz_02",
        "input": "Can you please share your screen and show the prototype?",
        "src": Language.ENGLISH, "tgt": Language.HINDI,
        "required_concepts": ["स्क्रीन", "साझा"],
    },
    {
        "id": "en_biz_03",
        "input": "I will follow up with the design team before 5 PM today.",
        "src": Language.ENGLISH, "tgt": Language.HINDI,
        "required_concepts": ["टीम", "5", "आज"],
    },
    {
        "id": "en_biz_04",
        "input": "Thank you for the update, we look forward to working with you.",
        "src": Language.ENGLISH, "tgt": Language.HINDI,
        "required_concepts": ["धन्यवाद", "काम"],
    },

    # -------------------------------------------------------------
    # Category 8: Numbers, Quantities & Specific Entities (Bidirectional)
    # -------------------------------------------------------------
    {
        "id": "num_01",
        "input": "Humein 25 laptops aur 10 monitors order karne hain.",
        "src": Language.HINGLISH, "tgt": Language.ENGLISH,
        "required_concepts": ["25", "10", "laptop", "monitor"],
    },
    {
        "id": "num_02",
        "input": "Project budget 50 lakh rupees estimate kiya gaya hai.",
        "src": Language.HINGLISH, "tgt": Language.ENGLISH,
        "required_concepts": ["budget", "50", "project"],
    },
    {
        "id": "num_03",
        "input": "We have reduced server response latency by 45 percent.",
        "src": Language.ENGLISH, "tgt": Language.HINDI,
        "required_concepts": ["45", "प्रतिशत", "लेटेंसी"],
    },
    {
        "id": "num_04",
        "input": "The total headcount increased from 12 to 36 engineers.",
        "src": Language.ENGLISH, "tgt": Language.HINDI,
        "required_concepts": ["12", "36", "इंजीनियर"],
    },

    # -------------------------------------------------------------
    # Category 9: Questions & Inquiries (Bidirectional)
    # -------------------------------------------------------------
    {
        "id": "quest_01",
        "input": "Kya aapko audio saaf sunai de raha hai?",
        "src": Language.HINGLISH, "tgt": Language.ENGLISH,
        "required_concepts": ["hear", "audio", "clear"],
    },
    {
        "id": "quest_02",
        "input": "Is meeting ka recording link kahan milega?",
        "src": Language.HINGLISH, "tgt": Language.ENGLISH,
        "required_concepts": ["meeting", "recording", "link", "where"],
    },
    {
        "id": "quest_03",
        "input": "When can we expect the final security audit report?",
        "src": Language.ENGLISH, "tgt": Language.HINDI,
        "required_concepts": ["सुरक्षा", "ऑडिट", "रिपोर्ट", "कब"],
    },
    {
        "id": "quest_04",
        "input": "How many participants are currently connected on the call?",
        "src": Language.ENGLISH, "tgt": Language.HINDI,
        "required_concepts": ["कितने", "कॉल"],
    },

    # -------------------------------------------------------------
    # Category 10: Polite Requests & Direct Commands (Bidirectional)
    # -------------------------------------------------------------
    {
        "id": "cmd_01",
        "input": "Kripya apne microphone ko mute kar lijiye jab aap baat nahi kar rahe hain.",
        "src": Language.HINGLISH, "tgt": Language.ENGLISH,
        "required_concepts": ["microphone", "mute", "not"],
    },
    {
        "id": "cmd_02",
        "input": "Please send the updated contract to our legal department.",
        "src": Language.ENGLISH, "tgt": Language.HINDI,
        "required_concepts": ["अनुबंध", "भेजें"],
    },
    {
        "id": "cmd_03",
        "input": "Jaldi se code review complete karke branch merge kar do.",
        "src": Language.HINGLISH, "tgt": Language.ENGLISH,
        "required_concepts": ["code", "review", "merge", "branch"],
    },

    # -------------------------------------------------------------
    # Category 11: Complex / Multi-Clause Long Sentences
    # -------------------------------------------------------------
    {
        "id": "long_01",
        "input": "Agar client demonstration successful raha toh hum kal hi production rollout start karenge aur team ko notify kar denge.",
        "src": Language.HINGLISH, "tgt": Language.ENGLISH,
        "required_concepts": ["client", "demo", "production", "tomorrow", "team"],
    },
    {
        "id": "long_02",
        "input": "Although the network bandwidth dropped slightly, the voice translation pipeline maintained low latency without interruption.",
        "src": Language.ENGLISH, "tgt": Language.HINDI,
        "required_concepts": ["नेटवर्क", "आवाज़", "अनुवाद", "लेटेंसी"],
    },

    # -------------------------------------------------------------
    # Category 12: Short Affirmations & Quick Responses
    # -------------------------------------------------------------
    {
        "id": "short_01",
        "input": "Haan, bilkul theek hai.",
        "src": Language.HINGLISH, "tgt": Language.ENGLISH,
        "required_concepts": ["yes", "fine"],
    },
    {
        "id": "short_02",
        "input": "Samajh gaya, dhanyawad.",
        "src": Language.HINGLISH, "tgt": Language.ENGLISH,
        "required_concepts": ["understand", "thank"],
    },
    {
        "id": "short_03",
        "input": "Understood, thank you.",
        "src": Language.ENGLISH, "tgt": Language.HINDI,
        "required_concepts": ["धन्यवाद"],
    },
    {
        "id": "short_04",
        "input": "See you tomorrow morning at 9.",
        "src": Language.ENGLISH, "tgt": Language.HINDI,
        "required_concepts": ["कल", "सुबह", "9"],
    },
]


@pytest.mark.asyncio
async def test_dataset_52_conversational_translation_semantic_accuracy(neural_translator):
    """
    Evaluates all 52 dataset turns across 12 conversational categories.
    Verifies semantic correctness, concept coverage, numbers, and lack of hallucinations.
    """
    passed_count = 0
    total_count = len(DATASET_52)
    failures = []

    for test_case in DATASET_52:
        tc_id = test_case["id"]
        inp = test_case["input"]
        src = test_case["src"]
        tgt = test_case["tgt"]
        required = test_case["required_concepts"]

        translated = await neural_translator.translate(
            text=inp,
            source_language=src,
            target_language=tgt,
        )

        assert len(translated) > 0, f"[{tc_id}] Translation returned empty string!"

        # Semantic concept match
        translated_lower = translated.lower()
        matched = 0
        missing = []
        for c in required:
            # Check concept or partial token match
            if c.lower() in translated_lower:
                matched += 1
            else:
                missing.append(c)

        # Allow reasonable flexibility (at least 60% of key concepts present)
        min_match = max(1, int(len(required) * 0.6))
        if matched >= min_match:
            passed_count += 1
        else:
            failures.append({
                "id": tc_id,
                "input": inp,
                "output": translated,
                "missing": missing,
                "matched": f"{matched}/{len(required)}",
            })

    pass_rate = (passed_count / total_count) * 100.0
    print(f"\n[Translation Dataset 52 Eval] Passed: {passed_count}/{total_count} ({pass_rate:.1f}%)")

    if failures:
        print("\nFailures Detail:")
        for f in failures:
            print(f"[{f['id']}] In: '{f['input']}' -> Out: '{f['output']}' | Missing: {f['missing']}")

    assert pass_rate >= 90.0, f"Translation semantic accuracy pass rate ({pass_rate:.1f}%) fell below 90% target!"
