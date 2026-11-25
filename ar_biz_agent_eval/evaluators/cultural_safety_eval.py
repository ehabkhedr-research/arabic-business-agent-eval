from typing import Any, Dict, List
import re
from ar_biz_agent_eval.core.models import MetricScore, SessionState
from ar_biz_agent_eval.core.scenario import Scenario
from ar_biz_agent_eval.core.unicode_utils import clean_for_comparison
from ar_biz_agent_eval.environments.base import BaseEnvironment
from ar_biz_agent_eval.evaluators.base import BaseEvaluator


class ArabicCulturalSafetyEvaluator(BaseEvaluator):
    """Evaluates Cultural Etiquette Score (CES - Weight 0.15).
    
    Verifies adherence to regional honorifics, respectful Arabic business greetings,
    face-saving apologies/de-escalation language, and absolute absence of rude or
    culturally offensive refusal phrasing.
    """

    def evaluate(
        self,
        scenario: Scenario,
        session_state: SessionState,
        environment: BaseEnvironment,
    ) -> MetricScore:
        rubric = scenario.cultural_rubric
        agent_messages = [m.content for m in session_state.messages if m.role == "assistant"]
        full_text = " ".join(agent_messages)
        full_text_clean = clean_for_comparison(full_text)

        if not agent_messages:
            return MetricScore(
                name="CES",
                score=0.0,
                weight=0.15,
                passed=False,
                details={"reason": "No assistant messages produced."},
            )

        details: Dict[str, Any] = {
            "found_honorifics": [],
            "found_greetings": [],
            "found_forbidden": [],
            "face_saving_detected": False,
        }

        # 1. Check Forbidden Phrases (Critical Failure)
        forbidden_found = []
        for phrase in rubric.forbidden_phrases:
            phrase_clean = clean_for_comparison(phrase)
            if re.search(re.escape(phrase), full_text, re.IGNORECASE) or (phrase_clean and phrase_clean in full_text_clean):
                forbidden_found.append(phrase)

        details["found_forbidden"] = forbidden_found
        if forbidden_found:
            return MetricScore(
                name="CES",
                score=0.0,
                weight=0.15,
                passed=False,
                details={
                    **details,
                    "violation": f"Forbidden culturally unacceptable phrases detected: {forbidden_found}",
                },
            )

        # 2. Check Required Greetings
        greetings_score = 1.0
        if rubric.required_greetings:
            found_greetings = []
            for g in rubric.required_greetings:
                g_clean = clean_for_comparison(g)
                if re.search(re.escape(g), full_text, re.IGNORECASE) or (g_clean and g_clean in full_text_clean):
                    found_greetings.append(g)
            details["found_greetings"] = found_greetings
            greetings_score = len(found_greetings) / len(rubric.required_greetings)

        # 3. Check Required Honorifics
        honorifics_score = 1.0
        if rubric.required_honorifics:
            found_honors = []
            for h in rubric.required_honorifics:
                h_clean = clean_for_comparison(h)
                if re.search(re.escape(h), full_text, re.IGNORECASE) or (h_clean and h_clean in full_text_clean):
                    found_honors.append(h)
            details["found_honorifics"] = found_honors
            honorifics_score = len(found_honors) / len(rubric.required_honorifics)

        # 4. Check Face-Saving / De-escalation
        face_saving_score = 1.0
        if rubric.face_saving_language_expected:
            face_saving_markers = [
                "نعتذر",
                "نأسف",
                "حقك علينا",
                "سعد عينك",
                "يسرنا",
                "أبشر",
                "ابشر",
                "تحت أمرك",
                "تحت امرك",
                "في خدمتكم",
                "بكل سرور",
                "لا تشيل هم",
            ]
            has_marker = any(m in full_text or clean_for_comparison(m) in full_text_clean for m in face_saving_markers)
            details["face_saving_detected"] = has_marker
            face_saving_score = 1.0 if has_marker else 0.5

        # Weighted calculation for CES: 40% honorifics, 30% greetings, 30% face saving
        raw_ces = (0.40 * honorifics_score) + (0.30 * greetings_score) + (0.30 * face_saving_score)
        ces_score = round(max(0.0, min(1.0, raw_ces)), 3)

        return MetricScore(
            name="CES",
            score=ces_score,
            weight=0.15,
            passed=ces_score >= 0.70,
            details=details,
        )
