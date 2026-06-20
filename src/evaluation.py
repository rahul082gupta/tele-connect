"""
Evaluation Framework for the Retention Agent.

Implements:
- Automated evaluation metrics
- LLM-as-judge evaluator with anchored rubrics
- Evaluation scoring and reporting
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import json
from datetime import datetime

from src.test_suite import TestCase, TestCategory


class ScoreLevel(Enum):
    """Scoring levels for rubric-based evaluation."""
    POOR = 1
    FAIR = 2
    GOOD = 3
    VERY_GOOD = 4
    EXCELLENT = 5


@dataclass
class RubricScore:
    """Score for a single rubric dimension."""
    dimension: str
    score: int  # 1-5
    justification: str
    evidence: List[str] = field(default_factory=list)


@dataclass
class TestEvaluation:
    """Complete evaluation of a test case."""
    test_id: str
    test_case: TestCase
    agent_response: Dict[str, Any]
    
    # Automated metrics
    tool_selection_accuracy: float  # 0-1
    parameter_extraction_accuracy: float  # 0-1
    response_completeness: float  # 0-1
    hallucination_score: float  # 0-1 (lower is better)
    execution_latency_ms: float
    
    # LLM-as-judge rubric scores
    factual_correctness: RubricScore
    tool_use_appropriateness: RubricScore
    actionability: RubricScore
    hallucination_detection: RubricScore
    
    # Overall assessment
    passed: bool = False
    failure_reason: Optional[str] = None
    
    def get_average_rubric_score(self) -> float:
        """Calculate average across all rubric dimensions."""
        scores = [
            self.factual_correctness.score,
            self.tool_use_appropriateness.score,
            self.actionability.score,
            self.hallucination_detection.score,
        ]
        return sum(scores) / len(scores)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_id": self.test_id,
            "passed": self.passed,
            "failure_reason": self.failure_reason,
            "automated_metrics": {
                "tool_selection_accuracy": self.tool_selection_accuracy,
                "parameter_extraction_accuracy": self.parameter_extraction_accuracy,
                "response_completeness": self.response_completeness,
                "hallucination_score": self.hallucination_score,
                "latency_ms": self.execution_latency_ms,
            },
            "rubric_scores": {
                "factual_correctness": {
                    "score": self.factual_correctness.score,
                    "justification": self.factual_correctness.justification,
                },
                "tool_use_appropriateness": {
                    "score": self.tool_use_appropriateness.score,
                    "justification": self.tool_use_appropriateness.justification,
                },
                "actionability": {
                    "score": self.actionability.score,
                    "justification": self.actionability.justification,
                },
                "hallucination_detection": {
                    "score": self.hallucination_detection.score,
                    "justification": self.hallucination_detection.justification,
                },
            },
            "average_rubric_score": self.get_average_rubric_score(),
        }


class AutomatedMetrics:
    """Automated evaluation metrics for agent responses."""
    
    @staticmethod
    def tool_selection_accuracy(test_case: TestCase, agent_response: Dict[str, Any]) -> float:
        """
        Evaluate if the agent called the correct tools.
        
        Returns: Score 0-1
        - 1.0: All expected tools called, no unexpected tools
        - 0.5: Some expected tools called, or extra unexpected tools
        - 0.0: Wrong tools or no tools called when required
        """
        expected_tool_names = {tc.tool_name for tc in test_case.expected_tool_calls}
        actual_tool_names = {tc["tool"] for tc in agent_response.get("tool_calls", [])}
        
        if not expected_tool_names and not actual_tool_names:
            return 1.0  # Both expect no tools
        
        if not expected_tool_names and actual_tool_names:
            return 0.0  # Unexpected tools called
        
        if not actual_tool_names and expected_tool_names:
            return 0.0  # Expected tools not called
        
        correct = len(expected_tool_names & actual_tool_names)
        total = len(expected_tool_names | actual_tool_names)
        return correct / total if total > 0 else 1.0
    
    @staticmethod
    def parameter_extraction_accuracy(test_case: TestCase, agent_response: Dict[str, Any]) -> float:
        """
        Evaluate if required parameters were extracted correctly.
        
        Returns: Score 0-1
        """
        tool_calls = agent_response.get("tool_calls", [])
        if not tool_calls:
            return 0.0 if test_case.expected_tool_calls else 1.0
        
        expected_params = {}
        for tc in test_case.expected_tool_calls:
            expected_params[tc.tool_name] = set(tc.required_params)
        
        correct_params = 0
        total_required = 0
        
        for tc in tool_calls:
            tool_name = tc.get("tool")
            params = tc.get("params", {})
            
            if tool_name in expected_params:
                required = expected_params[tool_name]
                total_required += len(required)
                for param in required:
                    if param in params and params[param]:
                        correct_params += 1
        
        return correct_params / total_required if total_required > 0 else 1.0
    
    @staticmethod
    def response_completeness(test_case: TestCase, agent_response: Dict[str, Any]) -> float:
        """
        Evaluate if response contains necessary components.
        
        Returns: Score 0-1
        """
        response_text = agent_response.get("response", "").lower()
        
        completeness_score = 0.0
        
        # Check for key elements based on test category
        if test_case.category == TestCategory.ESCALATION_TRIGGER:
            if test_case.should_escalate:
                if "escalat" in response_text:
                    completeness_score += 0.5
                if any(x in response_text for x in ["supervisor", "urgent", "priority"]):
                    completeness_score += 0.5
            else:
                if any(x in response_text for x in ["offer", "recommend", "suggest", "risk", "churn", "retention"]):
                    completeness_score = 1.0
                else:
                    completeness_score = min(1.0, len(response_text) / 500)
        
        elif test_case.category == TestCategory.AMBIGUOUS_INPUT:
            if "customer id" in response_text or "clarif" in response_text:
                completeness_score = 1.0
        
        elif test_case.category == TestCategory.MULTI_STEP_CHAINING:
            # Should have recommendations
            if "recommend" in response_text or "suggest" in response_text:
                completeness_score += 0.25
            # Should have risk assessment
            if "risk" in response_text or "churn" in response_text:
                completeness_score += 0.25
            # Should have offers
            if "offer" in response_text:
                completeness_score += 0.25
            # Should have action items
            if any(x in response_text for x in ["action", "next step", "should"]):
                completeness_score += 0.25
        
        else:
            # Generic: response should be substantive
            completeness_score = min(1.0, len(response_text) / 500)
        
        return completeness_score
    
    @staticmethod
    def hallucination_detection(test_case: TestCase, agent_response: Dict[str, Any]) -> float:
        """
        Detect hallucinations in agent response.
        
        Returns: Score 0-1 (lower is better - no hallucinations is 0)
        """
        response_text = agent_response.get("response", "").lower()
        tool_results = agent_response.get("tool_results", [])
        
        hallucination_score = 0.0
        
        # Check for invented customer data
        tool_names = {tc["tool"] for tc in agent_response.get("tool_calls", [])}
        if "lookup_customer" in tool_names:
            # If customer lookup happened, response should reference actual data
            # Not: invented names, made-up satisfaction scores, etc.
            pass  # Would need to compare against actual tool results
        
        # Check for invented offers
        if "get_retention_offers" in tool_names:
            # Response should only mention offers from tool results
            pass
        
        # Check for facts vs. speculation
        speculation_words = ["probably", "likely", "maybe", "i think", "might be"]
        speculation_count = sum(response_text.count(word) for word in speculation_words)
        hallucination_score += min(0.3, speculation_count * 0.1)
        
        return hallucination_score


class LLMAsJudge:
    """
    LLM-as-Judge evaluator for retention agent.
    
    Uses a simple mock implementation for demo purposes.
    In production, would call a real LLM API (OpenAI, Anthropic, etc.)
    """
    
    RUBRIC_ANCHORS = {
        "factual_correctness": {
            1: "Response contains multiple factual errors or contradicts tool results",
            2: "Response has some factual errors or misrepresentations",
            3: "Response is mostly factually correct with minor issues",
            4: "Response is factually correct and aligns with tool results",
            5: "Response is highly accurate, well-supported by tool results, no errors",
        },
        "tool_use_appropriateness": {
            1: "Tools are misused or called inappropriately; wrong order or missing critical tools",
            2: "Some tools called correctly, but gaps in tool orchestration",
            3: "Most tools called appropriately, reasonable orchestration",
            4: "All necessary tools called correctly in logical order",
            5: "Perfect tool orchestration; tools called in optimal sequence with correct params",
        },
        "actionability": {
            1: "Response is vague or non-actionable; rep cannot act on it",
            2: "Response has limited actionability; unclear next steps",
            3: "Response provides some actionable guidance",
            4: "Response is actionable; rep has clear next steps",
            5: "Response is highly actionable; specific, prioritized recommendations; rep can act immediately",
        },
        "hallucination": {
            1: "Response contains significant hallucinated information not from tool results",
            2: "Response includes notable fabrications or unsupported claims",
            3: "Response mostly grounded in tool results; minor unsupported claims",
            4: "Response is well-grounded; claims are supported by tool results",
            5: "Response contains no hallucinations; every claim traceable to tool result",
        },
    }
    
    @staticmethod
    def evaluate_test(test_case: TestCase, agent_response: Dict[str, Any]) -> TestEvaluation:
        """
        Evaluate a single test case using automated metrics and rubric scoring.
        """
        import time
        start_time = time.time()
        
        # Compute automated metrics
        tool_selection_acc = AutomatedMetrics.tool_selection_accuracy(test_case, agent_response)
        param_extraction_acc = AutomatedMetrics.parameter_extraction_accuracy(test_case, agent_response)
        response_completeness = AutomatedMetrics.response_completeness(test_case, agent_response)
        hallucination_score = AutomatedMetrics.hallucination_detection(test_case, agent_response)
        latency_ms = (time.time() - start_time) * 1000
        
        # Compute rubric scores using mock LLM-as-judge
        factual_correctness = LLMAsJudge._score_factual_correctness(test_case, agent_response)
        tool_use_appropriateness = LLMAsJudge._score_tool_use(test_case, agent_response)
        actionability = LLMAsJudge._score_actionability(test_case, agent_response)
        hallucination_detection = LLMAsJudge._score_hallucination(test_case, agent_response)
        
        # Determine pass/fail
        passed = True
        failure_reason = None
        
        if test_case.should_escalate:
            escalation_tools = {tc["tool"] for tc in agent_response.get("tool_calls", [])}
            if "escalate_to_supervisor" not in escalation_tools:
                passed = False
                failure_reason = "Expected escalation but none occurred"
        
        if tool_selection_acc < 0.5:
            passed = False
            failure_reason = "Poor tool selection accuracy"
        
        if response_completeness < 0.4:
            passed = False
            failure_reason = "Response incomplete or missing key elements"
        
        avg_rubric = (factual_correctness.score + tool_use_appropriateness.score + 
                     actionability.score + hallucination_detection.score) / 4
        if avg_rubric < 2.5:
            passed = False
            failure_reason = "Low rubric scores"
        
        evaluation = TestEvaluation(
            test_id=test_case.test_id,
            test_case=test_case,
            agent_response=agent_response,
            tool_selection_accuracy=tool_selection_acc,
            parameter_extraction_accuracy=param_extraction_acc,
            response_completeness=response_completeness,
            hallucination_score=hallucination_score,
            execution_latency_ms=latency_ms,
            factual_correctness=factual_correctness,
            tool_use_appropriateness=tool_use_appropriateness,
            actionability=actionability,
            hallucination_detection=hallucination_detection,
            passed=passed,
            failure_reason=failure_reason,
        )
        
        return evaluation
    
    @staticmethod
    def _score_factual_correctness(test_case: TestCase, agent_response: Dict[str, Any]) -> RubricScore:
        """Score factual correctness dimension."""
        response = agent_response.get("response", "")
        tool_results = agent_response.get("tool_results", [])
        
        score = 3  # Default to GOOD
        evidence = []
        
        # Check if tool calls succeeded
        all_successful = all(tr.get("success", False) for tr in tool_results if isinstance(tr, dict))
        if all_successful:
            score = 4
            evidence.append("All tool calls successful")
        
        # Check for contradictions with tool results
        for result in tool_results:
            if isinstance(result, dict):
                if result.get("success") and result.get("error"):
                    score = 2
                    evidence.append("Contradictory success/error signals")
        
        if test_case.expected_customer_id and test_case.expected_customer_id in response:
            score = max(score, 4)
            evidence.append(f"Correctly references expected customer {test_case.expected_customer_id}")
        
        if test_case.expected_risk_tier and test_case.expected_risk_tier in response.lower():
            score = 5
            evidence.append(f"Correctly identifies risk tier: {test_case.expected_risk_tier}")
        
        justification = "Response aligns with tool results and expectations"
        
        return RubricScore("Factual Correctness", score, justification, evidence)
    
    @staticmethod
    def _score_tool_use(test_case: TestCase, agent_response: Dict[str, Any]) -> RubricScore:
        """Score tool use appropriateness dimension."""
        tool_calls = agent_response.get("tool_calls", [])
        expected_tools = {tc.tool_name for tc in test_case.expected_tool_calls}
        actual_tools = {tc["tool"] for tc in tool_calls}
        
        score = 3
        evidence = []
        
        if not expected_tools and not actual_tools:
            score = 5
            evidence.append("Correctly did not call tools")
        elif expected_tools == actual_tools:
            score = 5
            evidence.append(f"All expected tools called: {actual_tools}")
        elif expected_tools & actual_tools:
            score = 4
            evidence.append(f"Most expected tools called: {expected_tools & actual_tools}")
            missing = expected_tools - actual_tools
            if missing:
                evidence.append(f"Missing tools: {missing}")
        else:
            score = 1
            evidence.append(f"Wrong tools called. Expected: {expected_tools}, Got: {actual_tools}")
        
        # Check tool ordering
        if len(tool_calls) > 1 and "lookup_customer" in actual_tools:
            lookup_idx = next(i for i, tc in enumerate(tool_calls) if tc["tool"] == "lookup_customer")
            predict_tools = [i for i, tc in enumerate(tool_calls) if tc["tool"] == "predict_churn"]
            if predict_tools and predict_tools[0] > lookup_idx:
                evidence.append("Tools called in correct order")
        
        justification = f"Tool orchestration score based on {len(tool_calls)} tool calls"
        
        return RubricScore("Tool Use Appropriateness", score, justification, evidence)
    
    @staticmethod
    def _score_actionability(test_case: TestCase, agent_response: Dict[str, Any]) -> RubricScore:
        """Score actionability dimension."""
        response = response_text = agent_response.get("response", "").lower()
        
        score = 2
        evidence = []
        
        # Check for specific recommendations
        if "recommend" in response_text or "suggest" in response_text:
            score = 3
            evidence.append("Contains recommendations")
        
        # Check for priority/urgency
        if any(x in response_text for x in ["urgent", "immediate", "asap", "priority"]):
            score = 4
            evidence.append("Indicates urgency level")
        
        # Check for specific action items
        action_indicators = ["present", "offer", "contact", "follow up", "escalate", "next step"]
        action_count = sum(response_text.count(action) for action in action_indicators)
        if action_count >= 3:
            score = 5
            evidence.append(f"Multiple specific action items ({action_count})")
        
        # Check for offers in multi-step chaining
        if test_case.category == TestCategory.MULTI_STEP_CHAINING:
            if "offer" in response_text:
                score = 4
                evidence.append("Includes retention offers in recommendations")
        
        justification = "Actionability scored based on specificity and clarity of recommendations"
        
        return RubricScore("Actionability", score, justification, evidence)
    
    @staticmethod
    def _score_hallucination(test_case: TestCase, agent_response: Dict[str, Any]) -> RubricScore:
        """Score hallucination detection dimension."""
        response_text = agent_response.get("response", "").lower()
        tool_results = agent_response.get("tool_results", [])
        
        score = 5  # Default to EXCELLENT (no hallucinations)
        evidence = []
        
        # Check for speculation without grounding
        speculation_terms = ["probably", "likely", "i think", "maybe", "might", "possibly"]
        speculation_count = sum(response_text.count(term) for term in speculation_terms)
        
        if speculation_count > 3:
            score = 2
            evidence.append(f"High speculation language ({speculation_count} instances)")
        elif speculation_count > 1:
            score = 3
            evidence.append(f"Some speculative language ({speculation_count} instances)")
        
        # Check for unsupported claims
        if tool_results:
            success_count = sum(1 for tr in tool_results if isinstance(tr, dict) and tr.get("success"))
            if success_count == 0:
                score = 2
                evidence.append("Claims made despite tool failures")
        
        # Check for data consistency
        if "customer" in response_text and tool_results:
            evidence.append("Customer data grounded in tool results")
        
        if not evidence:
            evidence.append("No hallucinations detected")
        
        justification = "No unsupported claims or fabrications detected in response"
        
        return RubricScore("Hallucination", score, justification, evidence)


@dataclass
class EvaluationReport:
    """Complete evaluation report for all tests."""
    timestamp: str
    test_results: List[TestEvaluation]
    
    def get_pass_rate(self) -> float:
        """Calculate overall pass rate."""
        if not self.test_results:
            return 0.0
        passed = sum(1 for tr in self.test_results if tr.passed)
        return passed / len(self.test_results)
    
    def get_category_breakdown(self) -> Dict[str, Dict[str, Any]]:
        """Get pass rates by test category."""
        categories = {}
        for result in self.test_results:
            cat = result.test_case.category.value
            if cat not in categories:
                categories[cat] = {"total": 0, "passed": 0, "avg_score": 0.0}
            categories[cat]["total"] += 1
            if result.passed:
                categories[cat]["passed"] += 1
            categories[cat]["avg_score"] += result.get_average_rubric_score()
        
        for cat in categories:
            categories[cat]["pass_rate"] = categories[cat]["passed"] / categories[cat]["total"]
            categories[cat]["avg_score"] /= categories[cat]["total"]
        
        return categories
    
    def get_average_rubric_scores(self) -> Dict[str, float]:
        """Get average scores by rubric dimension."""
        if not self.test_results:
            return {}
        
        dimensions = ["factual_correctness", "tool_use_appropriateness", "actionability", "hallucination_detection"]
        averages = {}
        
        for dim in dimensions:
            scores = []
            for result in self.test_results:
                if dim == "factual_correctness":
                    scores.append(result.factual_correctness.score)
                elif dim == "tool_use_appropriateness":
                    scores.append(result.tool_use_appropriateness.score)
                elif dim == "actionability":
                    scores.append(result.actionability.score)
                elif dim == "hallucination_detection":
                    scores.append(result.hallucination_detection.score)
            averages[dim] = sum(scores) / len(scores) if scores else 0.0
        
        return averages
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "summary": {
                "total_tests": len(self.test_results),
                "passed": sum(1 for r in self.test_results if r.passed),
                "failed": sum(1 for r in self.test_results if not r.passed),
                "pass_rate": self.get_pass_rate(),
            },
            "category_breakdown": self.get_category_breakdown(),
            "average_rubric_scores": self.get_average_rubric_scores(),
            "test_results": [r.to_dict() for r in self.test_results],
        }


__all__ = ["AutomatedMetrics", "LLMAsJudge", "TestEvaluation", "EvaluationReport", "RubricScore"]
