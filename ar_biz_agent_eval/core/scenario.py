"""Scenario schemas and dialect/domain definitions for Arabic benchmarks."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, model_validator


class DialectEnum(str, Enum):
    """Supported Arabic dialects and linguistic varieties."""

    MSA = "msa"  # Modern Standard Arabic (الفصحى الحديثة)
    GULF = "gulf"  # Khaleeji: Saudi, UAE, Kuwaiti, Qatari (اللهجة الخليجية)
    KHALEEJI = "khaleeji"  # Alias for Gulf
    EGYPTIAN = "egyptian"  # Egyptian Masri (اللهجة المصرية)
    MASRI = "masri"  # Alias for Egyptian
    LEVANTINE = "levantine"  # Shami: Syrian, Lebanese, Jordanian, Palestinian (اللهجة الشامية)
    SHAMI = "shami"  # Alias for Levantine
    MAGHREBI = "maghrebi"  # Maghrebi (اللهجة المغاربية)
    CODE_SWITCHING = "code_switching"  # Anglo-Arabic / Arabizi in Tech & Business
    CODE_SWITCH = "code_switch"  # Alias


class DomainEnum(str, Enum):
    """Core MENA business functional domains."""

    SALES = "sales"
    SALES_CRM = "sales_crm"
    SUPPORT = "support"
    SUPPORT_DISPUTE = "support_dispute"
    PROCUREMENT = "procurement"
    BILLING = "billing"
    BILLING_TAX = "billing_tax"
    CULTURAL_PROTOCOL = "cultural_protocol"


class ExpectedToolCall(BaseModel):
    """Specification of a tool call expected in a turn or scenario."""

    tool_name: Optional[str] = None
    function_name: Optional[str] = None
    arguments: Dict[str, Any] = Field(default_factory=dict)
    required_params: Dict[str, Any] = Field(default_factory=dict)
    optional_params: Dict[str, Any] = Field(default_factory=dict)
    order_matters: bool = False

    def model_post_init(self, __context: Any) -> None:
        if not self.tool_name and self.function_name:
            self.tool_name = self.function_name
        elif not self.function_name and self.tool_name:
            self.function_name = self.tool_name
        if not self.arguments and self.required_params:
            self.arguments = dict(self.required_params)
        elif not self.required_params and self.arguments:
            self.required_params = dict(self.arguments)

    @property
    def target_name(self) -> str:
        return self.tool_name or self.function_name or ""

    @property
    def target_args(self) -> Dict[str, Any]:
        combined = dict(self.required_params)
        combined.update(self.arguments)
        return combined


class Turn(BaseModel):
    """Single interactive step within an evaluation scenario."""

    turn_id: int = 1
    user_input: Optional[str] = None
    user_message: Optional[str] = None
    expected_intent: Optional[str] = None
    context_updates: Dict[str, Any] = Field(default_factory=dict)
    expected_tool_calls: List[ExpectedToolCall] = Field(default_factory=list)
    expected_outcomes: List[str] = Field(default_factory=list)
    expected_keywords_arabic: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def sync_user_text(self) -> Turn:
        text = self.user_input or self.user_message or ""
        self.user_input = text
        self.user_message = text
        return self

    @property
    def prompt(self) -> str:
        return self.user_input or self.user_message or ""


class StateAssertion(BaseModel):
    """Condition to check on environment state."""

    # Path-based style
    path: Optional[str] = None
    condition: str = "equals"  # equals, length_equals, contains, greater_than, is_true
    value: Optional[Any] = None

    # Entity-based style
    entity: Optional[str] = None
    target_id: Optional[str] = None
    field: Optional[str] = None
    expected_value: Optional[Any] = None
    operator: str = "=="

    @model_validator(mode="after")
    def sync_fields(self) -> StateAssertion:
        if self.value is not None and self.expected_value is None:
            self.expected_value = self.value
        elif self.expected_value is not None and self.value is None:
            self.value = self.expected_value
        return self


class CulturalEtiquetteRubric(BaseModel):
    """Cultural and linguistic rubric requirements."""

    required_honorifics: List[str] = Field(default_factory=list)
    required_greetings: List[str] = Field(default_factory=list)
    greeting_type: Optional[str] = None
    required_tone: Optional[str] = None
    forbidden_phrases: List[str] = Field(default_factory=list)
    face_saving_required: bool = False
    face_saving_language_expected: bool = False

    @model_validator(mode="after")
    def sync_face_saving(self) -> CulturalEtiquetteRubric:
        if self.face_saving_required and not self.face_saving_language_expected:
            self.face_saving_language_expected = True
        elif self.face_saving_language_expected and not self.face_saving_required:
            self.face_saving_required = True
        return self


class ExpectedOutcomes(BaseModel):
    """Top-level expected outcomes and criteria for scenario success."""

    mandatory_tool_calls: List[ExpectedToolCall] = Field(default_factory=list)
    forbidden_tool_calls: List[Union[ExpectedToolCall, Dict[str, Any]]] = Field(default_factory=list)
    state_assertions: List[StateAssertion] = Field(default_factory=list)


class EvaluationCriteria(BaseModel):
    """Ground-truth validation criteria for benchmark success."""

    golden_turn_count: int = 1
    max_allowed_turns: int = 3
    max_turns: int = Field(default=5, ge=1)
    passing_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    required_tools: List[str] = Field(default_factory=list)
    prohibited_tools: List[str] = Field(default_factory=list)
    target_state_assertions: Dict[str, Any] = Field(default_factory=dict)
    cultural_rules: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def sync_turn_limits(self) -> EvaluationCriteria:
        if self.max_allowed_turns != 3 and self.max_turns == 5:
            self.max_turns = self.max_allowed_turns
        elif self.max_turns != 5 and self.max_allowed_turns == 3:
            self.max_allowed_turns = self.max_turns
        return self


class ScenarioContext(dict):
    """Context dictionary supporting attribute access for convenience."""

    def __getattr__(self, item: str) -> Any:
        return self.get(item, "")

    def __setattr__(self, key: str, value: Any) -> None:
        self[key] = value


class Scenario(BaseModel):
    """Complete benchmark scenario definition."""

    schema_version: str = "1.0"
    id: str
    title: Union[str, Dict[str, str]] = ""
    description: Union[str, Dict[str, str]] = ""
    domain: DomainEnum
    dialect: DialectEnum
    complexity: str = "L2_MULTI_TURN"
    difficulty: str = "intermediate"
    system_prompt: str = Field(
        default="You are an autonomous AI business assistant for a leading enterprise in the MENA region. Assist professionally and use appropriate business tools when necessary.",
    )
    user_persona: Optional[Dict[str, Any]] = Field(default_factory=dict)
    initial_state: Dict[str, Any] = Field(default_factory=dict)
    context: Any = Field(default_factory=dict)
    turns: List[Turn] = Field(default_factory=list)
    dialogue_turns: Optional[List[Turn]] = Field(default_factory=list)
    expected_outcomes: Optional[ExpectedOutcomes] = None
    cultural_rubric: Optional[CulturalEtiquetteRubric] = None
    cultural_etiquette_rubric: Optional[CulturalEtiquetteRubric] = None
    state_assertions: List[StateAssertion] = Field(default_factory=list)
    evaluation_criteria: Optional[EvaluationCriteria] = None
    criteria: EvaluationCriteria = Field(default_factory=EvaluationCriteria)
    tags: List[str] = Field(default_factory=list)

    def model_post_init(self, __context: Any) -> None:
        # Reconcile dialogue_turns with turns
        if self.dialogue_turns and not self.turns:
            self.turns = list(self.dialogue_turns)
        elif self.turns and not self.dialogue_turns:
            self.dialogue_turns = list(self.turns)

        # Wrap context in ScenarioContext
        if isinstance(self.context, dict) and not isinstance(self.context, ScenarioContext):
            wrapped = ScenarioContext(self.context)
            if "business_context" not in wrapped and self.description_display:
                wrapped["business_context"] = self.description_display
            self.context = wrapped
        elif not self.context:
            self.context = ScenarioContext({"business_context": self.description_display})

        # Reconcile cultural_rubric with cultural_etiquette_rubric
        if self.cultural_etiquette_rubric is not None and self.cultural_rubric is None:
            self.cultural_rubric = self.cultural_etiquette_rubric
        elif self.cultural_rubric is not None and self.cultural_etiquette_rubric is None:
            self.cultural_etiquette_rubric = self.cultural_rubric
        elif self.cultural_rubric is None and self.cultural_etiquette_rubric is None:
            default_rubric = CulturalEtiquetteRubric()
            self.cultural_rubric = default_rubric
            self.cultural_etiquette_rubric = default_rubric

        # Reconcile criteria with evaluation_criteria
        if self.evaluation_criteria is not None:
            self.criteria = self.evaluation_criteria
        else:
            self.evaluation_criteria = self.criteria

        # Reconcile state_assertions with expected_outcomes.state_assertions
        if self.expected_outcomes and self.expected_outcomes.state_assertions and not self.state_assertions:
            self.state_assertions = list(self.expected_outcomes.state_assertions)
        elif self.state_assertions and (not self.expected_outcomes or not self.expected_outcomes.state_assertions):
            if self.expected_outcomes is None:
                self.expected_outcomes = ExpectedOutcomes(state_assertions=self.state_assertions)
            else:
                self.expected_outcomes.state_assertions = list(self.state_assertions)

        # Reconcile mandatory_tool_calls into turns
        if self.expected_outcomes and self.expected_outcomes.mandatory_tool_calls:
            if len(self.turns) == 1 and not self.turns[0].expected_tool_calls:
                self.turns[0].expected_tool_calls = list(self.expected_outcomes.mandatory_tool_calls)
            elif len(self.turns) > 1 and all(not t.expected_tool_calls for t in self.turns):
                remaining_calls = list(self.expected_outcomes.mandatory_tool_calls)
                for t in self.turns:
                    t_text = f"{t.expected_intent or ''} {t.user_input or ''}"
                    assigned = []
                    for c in remaining_calls:
                        target = c.target_name or c.tool_name or ""
                        if target.lower() in t_text.lower() or any(w in t_text.lower() for w in target.split("_")):
                            assigned.append(c)
                    for c in assigned:
                        remaining_calls.remove(c)
                    t.expected_tool_calls = assigned
                if remaining_calls and self.turns:
                    self.turns[-1].expected_tool_calls.extend(remaining_calls)

    @property
    def title_display(self) -> str:
        if isinstance(self.title, dict):
            ar = self.title.get("ar", "")
            en = self.title.get("en", "")
            return f"{ar} ({en})" if ar and en else (ar or en)
        return str(self.title)

    @property
    def description_display(self) -> str:
        if isinstance(self.description, dict):
            return self.description.get("ar") or self.description.get("en") or ""
        return str(self.description)

    @property
    def total_turns(self) -> int:
        return len(self.turns)
