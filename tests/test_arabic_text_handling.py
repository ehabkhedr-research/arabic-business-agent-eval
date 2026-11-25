import pytest
from ar_biz_agent_eval.core.models import Message, SessionState, ToolCall, ToolResult
from ar_biz_agent_eval.core.scenario import (
    CulturalEtiquetteRubric,
    EvaluationCriteria,
    ExpectedToolCall,
    Scenario,
    Turn,
    DialectEnum,
    DomainEnum,
)
from ar_biz_agent_eval.core.unicode_utils import (
    clean_for_comparison,
    contains_arabic,
    convert_arabic_digits,
    convert_to_eastern_digits,
    is_code_switched,
    normalize_arabic,
    strip_bidi_controls,
    strip_tashkeel,
    strip_tatweel,
)
from ar_biz_agent_eval.environments.business_suite import BusinessEnvironment
from ar_biz_agent_eval.evaluators.cultural_safety_eval import ArabicCulturalSafetyEvaluator
from ar_biz_agent_eval.evaluators.tool_call_eval import ToolCallEvaluator


def test_strip_tashkeel_diacritics():
    """Verify that Arabic diacritics (Harakat / Tashkeel) are cleanly removed."""
    diacritized_text = "السَّلَامُ عَلَيْكُمْ وَرَحْمَةُ اللهِ وَبَرَكَاتُهُ، نَرْجُو إِصْدَارَ الفَاتُورَةِ"
    stripped = strip_tashkeel(diacritized_text)
    assert stripped == "السلام عليكم ورحمة الله وبركاته، نرجو إصدار الفاتورة"
    assert "َ" not in stripped
    assert "ُ" not in stripped
    assert "ِ" not in stripped
    assert "ْ" not in stripped
    assert "ّ" not in stripped


def test_strip_tatweel_and_bidi():
    """Verify Tatweel (Kashida) and invisible Bidi directional control characters are stripped."""
    kashida_text = "شــــركــــة الأنــــوار الـــســـحـــابـــيـــة"
    stripped_kashida = strip_tatweel(kashida_text)
    assert stripped_kashida == "شركة الأنوار السحابية"

    # RTL and LTR mark embedding
    bidi_text = "\u200eشركة التقنية\u200f المحدودة\u202a (LLC)\u202c"
    stripped_bidi = strip_bidi_controls(bidi_text)
    assert "\u200e" not in stripped_bidi
    assert "\u200f" not in stripped_bidi
    assert "\u202a" not in stripped_bidi
    assert "\u202c" not in stripped_bidi


def test_eastern_arabic_numeral_conversion():
    """Verify Eastern Arabic-Indic numerals (٠-٩) and Persian numerals (۰-۹) are converted to ASCII."""
    eastern_phone = "+٩٦٦٥٠٠١١٢٢٣٣"
    converted_phone = convert_arabic_digits(eastern_phone)
    assert converted_phone == "+966500112233"

    eastern_vat = "٣٠٠٠٠٠٠٠٠٠٠٠٠٠٣"
    converted_vat = convert_arabic_digits(eastern_vat)
    assert converted_vat == "300000000000003"

    eastern_amount = "٥٧٥٠٠.٥٠"
    converted_amount = convert_arabic_digits(eastern_amount)
    assert converted_amount == "57500.50"
    assert float(converted_amount) == 57500.50

    # Round-trip conversion check
    western = "0123456789"
    eastern = convert_to_eastern_digits(western)
    assert eastern == "٠١٢٣٤٥٦٧٨٩"
    assert convert_arabic_digits(eastern) == western


def test_arabic_orthographic_normalization():
    """Verify normalization of Alef variants, Taa Marbuta, and Yaa."""
    # Alef variants: أ, إ, آ, ٱ -> ا
    text_alef = "أحمد وإبراهيم في آفاق الإبداع ٱلتقوا"
    norm_alef = normalize_arabic(text_alef)
    assert "أ" not in norm_alef
    assert "إ" not in norm_alef
    assert "آ" not in norm_alef
    assert "ٱ" not in norm_alef
    assert "احمد وابراهيم في افاق الابداع التقوا" in norm_alef

    # Taa Marbuta (ة -> ه)
    text_tm = "شركة، مؤسسة، تقنية، سحابية"
    norm_tm = normalize_arabic(text_tm)
    assert "ة" not in norm_tm
    assert "شركه، مؤسسه، تقنيه، سحابيه" == norm_tm

    # Yaa / Alef Maqsura (ى -> ي)
    text_yaa = "علي ومصطفى في المستشفى"
    norm_yaa = normalize_arabic(text_yaa)
    assert "ى" not in norm_yaa
    assert "علي ومصطفي في المستشفي" == norm_yaa


def test_clean_for_comparison():
    """Verify clean_for_comparison provides consistent representation for matching."""
    variant1 = "  شَرِكَةُ الأُفُقِ لِلْتَّقْنِيَّةِ  "
    variant2 = "شركة الافق للتقنيه"
    assert clean_for_comparison(variant1) == clean_for_comparison(variant2)

    honorific1 = "طَالَ عُمْرُكْ"
    honorific2 = "طال عمرك"
    assert clean_for_comparison(honorific1) == clean_for_comparison(honorific2)


def test_code_switching_and_arabic_detection():
    """Verify language detection and handling of mixed Anglo-Arabic business text."""
    pure_arabic = "نرجو تزويدنا بعرض سعر رسمي معتمد"
    assert contains_arabic(pure_arabic) is True
    assert is_code_switched(pure_arabic) is False

    pure_english = "Please provide the official SLA quotation"
    assert contains_arabic(pure_english) is False
    assert is_code_switched(pure_english) is False

    code_switched = "محتاجين نعمل deploy للـ solution على AWS وعايزين quotation للـ SLA"
    assert contains_arabic(code_switched) is True
    assert is_code_switched(code_switched) is True


def test_evaluator_parameter_extraction_with_arabic_numerals():
    """Verify ToolCallEvaluator matches arguments when agent outputs Eastern numerals or formatted strings."""
    evaluator = ToolCallEvaluator()
    env = BusinessEnvironment()

    scenario = Scenario(
        id="ARAB-TEST-UNICODE",
        title="Unicode Parameter Matching",
        domain=DomainEnum.BILLING,
        dialect=DialectEnum.KHALEEJI,
        difficulty="standard",
        description="Verify parameter normalization in evaluator",
        turns=[
            Turn(
                user_message="نبي فاتورة بـ ٥٠٠٠٠ ريال للرقم الضريبي ٣٠٠٠٠٠٠٠٠٠٠٠٠٠٣",
                expected_tool_calls=[
                    ExpectedToolCall(
                        tool_name="generate_tax_invoice",
                        arguments={
                            "customer_name": "شركة الخليج للتقنية",
                            "customer_vat_number": "300000000000003",
                            "currency": "SAR",
                        },
                    )
                ],
            )
        ],
        cultural_rubric=CulturalEtiquetteRubric(
            required_honorifics=["طال عمرك"],
            required_greetings=["حياك الله"],
        ),
    )

    session = SessionState(scenario_id="ARAB-TEST-UNICODE", agent_name="MockAgent")
    session.add_message(Message(role="user", content=scenario.turns[0].user_message))
    session.add_message(Message(role="assistant", content="حياك الله طال عمرك"))

    # Agent called tool with Eastern numerals for VAT number and slight orthographic difference in company name
    session.record_tool_call(
        ToolResult(
            tool_name="generate_tax_invoice",
            arguments={
                "customer_name": "شَرِكَةُ الخَلِيجِ لِلتَّقْنِيَّةِ",  # Diacritized
                "customer_vat_number": "٣٠٠٠٠٠٠٠٠٠٠٠٠٠٣",  # Eastern Arabic-Indic digits
                "currency": "sar",  # Lowercase
            },
            result={"status": "SUCCESS"},
            latency_seconds=0.01,
        )
    )

    metrics = evaluator.evaluate(scenario, session, env)
    pea = next(m for m in metrics if m.name == "PEA")
    avr = next(m for m in metrics if m.name == "AVR")

    assert avr.score == 1.0
    assert pea.score == 1.0  # Perfect parameter match despite diacritics and eastern numerals
    assert pea.passed is True


def test_cultural_safety_evaluator_with_diacritized_honorifics():
    """Verify ArabicCulturalSafetyEvaluator detects honorifics and greetings even when diacritized."""
    evaluator = ArabicCulturalSafetyEvaluator()
    env = BusinessEnvironment()

    scenario = Scenario(
        id="ARAB-TEST-CES",
        title="CES Unicode Test",
        domain=DomainEnum.SALES,
        dialect=DialectEnum.KHALEEJI,
        difficulty="standard",
        description="Test CES with diacritics",
        turns=[Turn(user_message="السلام عليكم")],
        cultural_rubric=CulturalEtiquetteRubric(
            required_honorifics=["طال عمرك", "سعادتكم"],
            required_greetings=["حياك الله"],
            forbidden_phrases=["ادفع أولاً"],
            face_saving_language_expected=True,
        ),
    )

    session = SessionState(scenario_id="ARAB-TEST-CES", agent_name="MockAgent")
    # Assistant response with full Tashkeel
    session.add_message(
        Message(
            role="assistant",
            content="حَيَّاكَ اللهُ طَالَ عُمْرُكَ وَسَعَادَتَكُمْ، أَبْشِرْ بِكُلِّ خَيْرٍ وَفِي خِدْمَتِكُمْ دَائِمًا.",
        )
    )

    ces = evaluator.evaluate(scenario, session, env)
    assert ces.passed is True
    assert ces.score == 1.0
    assert "طال عمرك" in ces.details["found_honorifics"]
    assert "حياك الله" in ces.details["found_greetings"]
    assert ces.details["face_saving_detected"] is True
