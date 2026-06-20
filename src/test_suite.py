"""
Structured Test Suite for the Retention Agent.

This module defines 12+ test cases covering:
- Single-tool happy path
- Multi-step tool chaining
- Ambiguous input handling
- Out-of-scope requests
- Escalation triggers
- Model disagreement scenarios
- Edge cases
"""

from typing import Any, Dict, List
from dataclasses import dataclass, field
from enum import Enum


class TestCategory(Enum):
    """Test case categories."""
    SINGLE_TOOL_HAPPY_PATH = "single_tool_happy_path"
    MULTI_STEP_CHAINING = "multi_step_chaining"
    AMBIGUOUS_INPUT = "ambiguous_input"
    OUT_OF_SCOPE = "out_of_scope"
    ESCALATION_TRIGGER = "escalation_trigger"
    MODEL_DISAGREEMENT = "model_disagreement"
    EDGE_CASE = "edge_case"
    ERROR_HANDLING = "error_handling"


class ExpectedToolCall:
    """Expected tool call in a test case."""
    def __init__(self, tool_name: str, required_params: List[str] = None, optional_params: List[str] = None):
        self.tool_name = tool_name
        self.required_params = required_params or []
        self.optional_params = optional_params or []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool": self.tool_name,
            "required_params": self.required_params,
            "optional_params": self.optional_params,
        }


@dataclass
class TestCase:
    """Represents a test case for the retention agent."""
    test_id: str
    category: TestCategory
    description: str
    user_input: str
    expected_tool_calls: List[ExpectedToolCall]
    quality_criteria: List[str]
    should_escalate: bool = False
    expected_customer_id: str = None
    expected_risk_tier: str = None
    notes: str = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_id": self.test_id,
            "category": self.category.value,
            "description": self.description,
            "user_input": self.user_input,
            "expected_tool_calls": [tc.to_dict() for tc in self.expected_tool_calls],
            "quality_criteria": self.quality_criteria,
            "should_escalate": self.should_escalate,
            "expected_customer_id": self.expected_customer_id,
            "expected_risk_tier": self.expected_risk_tier,
            "notes": self.notes,
        }


# ========== TEST SUITE ==========

TEST_SUITE: List[TestCase] = [
    # ========== 1. SINGLE-TOOL HAPPY PATH ==========
    TestCase(
        test_id="T001",
        category=TestCategory.SINGLE_TOOL_HAPPY_PATH,
        description="Customer lookup by explicit ID",
        user_input="Can you look up CUST001 for me?",
        expected_tool_calls=[
            ExpectedToolCall("lookup_customer", ["customer_id"]),
        ],
        quality_criteria=[
            "Successfully retrieves customer CUST001",
            "Response includes customer name and tenure",
            "Response is formatted clearly",
        ],
        expected_customer_id="CUST001",
        notes="Basic lookup should work without additional context",
    ),
    
    # ========== 2. MULTI-STEP CHAINING ==========
    TestCase(
        test_id="T002",
        category=TestCategory.MULTI_STEP_CHAINING,
        description="Full analysis chain: lookup → predict → offers",
        user_input="I have a customer CUST001 on the phone. Need retention recommendations.",
        expected_tool_calls=[
            ExpectedToolCall("lookup_customer", ["customer_id"]),
            ExpectedToolCall("predict_churn", ["age", "gender", "tenure_months", "contract_type", "monthly_charges"]),
            ExpectedToolCall("get_retention_offers", ["risk_tier", "contract_type"]),
            ExpectedToolCall("log_interaction", ["customer_id", "interaction_type"]),
        ],
        quality_criteria=[
            "Tools called in correct order",
            "All 4 tools are invoked",
            "Response includes churn probability",
            "Response includes retention offers",
            "Recommendations are actionable",
        ],
        expected_customer_id="CUST001",
        notes="Standard happy path for retention rep workflow",
    ),
    
    TestCase(
        test_id="T003",
        category=TestCategory.MULTI_STEP_CHAINING,
        description="Multi-step analysis for high-risk customer",
        user_input="Check on CUST003 - I think they might churn soon",
        expected_tool_calls=[
            ExpectedToolCall("lookup_customer", ["customer_id"]),
            ExpectedToolCall("predict_churn", ["age", "gender", "tenure_months", "contract_type", "monthly_charges"]),
            ExpectedToolCall("get_retention_offers", ["risk_tier", "contract_type"]),
            ExpectedToolCall("log_interaction", ["customer_id"]),
        ],
        quality_criteria=[
            "Identifies high-risk signals",
            "Suggests urgent action",
            "Offers are tailored to risk level",
            "Response tone reflects urgency",
        ],
        expected_customer_id="CUST003",
        expected_risk_tier="high",
        notes="Agent should recognize high-risk profile and escalate urgency",
    ),
    
    # ========== 3. AMBIGUOUS INPUT HANDLING ==========
    TestCase(
        test_id="T004",
        category=TestCategory.AMBIGUOUS_INPUT,
        description="Missing customer ID - agent should ask for clarification",
        user_input="I have a high-risk customer on the phone",
        expected_tool_calls=[],
        quality_criteria=[
            "Agent asks for customer ID",
            "Response lists available test customers",
            "Does not make tool calls without customer ID",
            "Response is helpful and not dismissive",
        ],
        expected_customer_id=None,
        notes="Agent should gracefully handle missing critical info",
    ),
    
    TestCase(
        test_id="T005",
        category=TestCategory.AMBIGUOUS_INPUT,
        description="Vague customer reference",
        user_input="Can you help with the Smith customer who called earlier?",
        expected_tool_calls=[],
        quality_criteria=[
            "Agent recognizes ambiguity",
            "Asks for specific customer ID",
            "Does not guess or hallucinate customer ID",
            "Remains helpful and professional",
        ],
        expected_customer_id=None,
        notes="Ambiguous names should not lead to guessing",
    ),
    
    TestCase(
        test_id="T006",
        category=TestCategory.AMBIGUOUS_INPUT,
        description="Partial customer ID",
        user_input="Look up CUST for me",
        expected_tool_calls=[],
        quality_criteria=[
            "Agent recognizes incomplete ID",
            "Asks for full customer ID",
            "Suggests valid format (CUST###)",
        ],
        expected_customer_id=None,
        notes="Partial or malformed IDs should not be assumed",
    ),
    
    # ========== 4. OUT-OF-SCOPE REQUESTS ==========
    TestCase(
        test_id="T007",
        category=TestCategory.OUT_OF_SCOPE,
        description="Request to modify customer account",
        user_input="Can you change CUST001's contract to a 2-year plan?",
        expected_tool_calls=[],
        quality_criteria=[
            "Agent recognizes out-of-scope action",
            "Politely declines and explains limitations",
            "Suggests human-appropriate solution",
            "Does not attempt unauthorized changes",
        ],
        notes="Agent should recognize boundaries of its capabilities",
    ),
    
    TestCase(
        test_id="T008",
        category=TestCategory.OUT_OF_SCOPE,
        description="Request for unrelated information",
        user_input="What's the weather like today?",
        expected_tool_calls=[],
        quality_criteria=[
            "Agent politely redirects to retention context",
            "Refocuses on available tools",
            "Maintains professional tone",
        ],
        notes="Agent should stay focused on retention domain",
    ),
    
    # ========== 5. ESCALATION TRIGGERS ==========
    TestCase(
        test_id="T009",
        category=TestCategory.ESCALATION_TRIGGER,
        description="Legal threat escalation",
        user_input="CUST001 is threatening legal action if we don't fix their billing issue",
        expected_tool_calls=[
            ExpectedToolCall("escalate_to_supervisor", ["customer_id", "reason"]),
        ],
        quality_criteria=[
            "Escalation tool is called",
            "Escalation reason includes 'legal'",
            "No attempt to handle independently",
            "Response acknowledges seriousness",
            "Supervisor notification is confirmed",
        ],
        should_escalate=True,
        expected_customer_id="CUST001",
        notes="Legal threats should trigger immediate escalation",
    ),
    
    TestCase(
        test_id="T010",
        category=TestCategory.ESCALATION_TRIGGER,
        description="Customer complaint and frustration",
        user_input="CUST002 is very angry and wants to cancel immediately. They're complaining about service quality.",
        expected_tool_calls=[
            ExpectedToolCall("escalate_to_supervisor", ["customer_id", "reason"]),
        ],
        quality_criteria=[
            "Recognizes high-urgency situation",
            "Escalation is called",
            "Priority is marked as 'high' or 'urgent'",
            "Response shows empathy",
        ],
        should_escalate=True,
        expected_customer_id="CUST002",
        notes="Angry customers threatening cancellation should escalate",
    ),
    
    TestCase(
        test_id="T011",
        category=TestCategory.ESCALATION_TRIGGER,
        description="Customer considering competitor switch",
        user_input="CUST003 said a competitor offered them a better deal. Should I match it?",
        expected_tool_calls=[
            ExpectedToolCall("lookup_customer", ["customer_id"]),
            ExpectedToolCall("predict_churn", ["age", "gender", "tenure_months", "contract_type", "monthly_charges"]),
            ExpectedToolCall("get_retention_offers", ["risk_tier", "contract_type"]),
        ],
        quality_criteria=[
            "Does not automatically escalate",
            "Provides retention offers from catalog",
            "Explains offer limits professionally",
            "Suggests mentioning competitor offer in conversation",
        ],
        should_escalate=False,
        expected_customer_id="CUST003",
        notes="Competitor comparison is handleable at rep level with offers",
    ),
    
    # ========== 6. MODEL DISAGREEMENT SCENARIOS ==========
    TestCase(
        test_id="T012",
        category=TestCategory.MODEL_DISAGREEMENT,
        description="Low-risk profile with warning signs",
        user_input="CUST002 has low satisfaction score and many support tickets. Model says low risk though?",
        expected_tool_calls=[
            ExpectedToolCall("lookup_customer", ["customer_id"]),
            ExpectedToolCall("predict_churn", ["age", "gender", "tenure_months", "contract_type", "monthly_charges"]),
        ],
        quality_criteria=[
            "Response acknowledges profile contradictions",
            "Respects model output but notes caution",
            "Recommends close monitoring",
            "Suggests follow-up contact",
        ],
        expected_customer_id="CUST002",
        notes="Agent should flag when intuition conflicts with model",
    ),
    
    # ========== 7. EDGE CASES ==========
    TestCase(
        test_id="T013",
        category=TestCategory.EDGE_CASE,
        description="Very new customer (0 tenure)",
        user_input="New customer just signed up today - what's their churn risk?",
        expected_tool_calls=[],
        quality_criteria=[
            "Agent handles zero-tenure edge case gracefully",
            "Explains lack of historical data",
            "Suggests onboarding follow-up instead",
            "Does not attempt prediction on insufficient data",
        ],
        notes="Edge case: brand new customer has no history",
    ),
    
    TestCase(
        test_id="T014",
        category=TestCategory.EDGE_CASE,
        description="Extremely long-tenure customer (24+ years)",
        user_input="Long-term customer CUST999 with 300+ months tenure - need to check status",
        expected_tool_calls=[],
        quality_criteria=[
            "Agent handles invalid customer ID gracefully",
            "Suggests valid test customers",
            "Does not error on non-existent ID",
        ],
        expected_customer_id=None,
        notes="Test handling of non-existent customers",
    ),
]


def get_test_suite() -> List[TestCase]:
    """Get the complete test suite."""
    return TEST_SUITE


def get_tests_by_category(category: TestCategory) -> List[TestCase]:
    """Get tests filtered by category."""
    return [t for t in TEST_SUITE if t.category == category]


def get_test_summary() -> Dict[str, Any]:
    """Get summary statistics of the test suite."""
    categories = {}
    for test in TEST_SUITE:
        cat_name = test.category.value
        if cat_name not in categories:
            categories[cat_name] = 0
        categories[cat_name] += 1
    
    return {
        "total_tests": len(TEST_SUITE),
        "by_category": categories,
        "test_ids": [t.test_id for t in TEST_SUITE],
    }


# Export for convenience
__all__ = ["TestCase", "TestCategory", "TEST_SUITE", "get_test_suite", "get_tests_by_category", "get_test_summary"]
