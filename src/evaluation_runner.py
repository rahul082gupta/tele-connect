"""
Evaluation Runner for the Retention Agent.

Executes all tests and generates comprehensive evaluation reports.
"""

import time
import json
from typing import List, Dict, Any
from datetime import datetime

from src.agent import RetentionAgent
from src.test_suite import get_test_suite, TestCase, get_test_summary
from src.evaluation import LLMAsJudge, EvaluationReport, TestEvaluation


class EvaluationRunner:
    """Runs the complete evaluation suite for the agent."""
    
    def __init__(self):
        self.agent = RetentionAgent()
        self.test_suite = get_test_suite()
        self.results: List[TestEvaluation] = []
    
    def run_single_test(self, test_case: TestCase) -> TestEvaluation:
        """Run a single test case."""
        # Reset agent for fresh state
        self.agent.reset_conversation()
        
        # Run the test
        start_time = time.time()
        agent_response = self.agent.process_user_input(test_case.user_input)
        elapsed_time = time.time() - start_time
        
        # Evaluate the response
        evaluation = LLMAsJudge.evaluate_test(test_case, agent_response)
        evaluation.execution_latency_ms = elapsed_time * 1000
        
        return evaluation
    
    def run_all_tests(self, verbose: bool = True) -> EvaluationReport:
        """Run all tests in the suite."""
        self.results = []
        
        if verbose:
            print(f"\n{'='*80}")
            print("RETENTION AGENT EVALUATION SUITE")
            print(f"{'='*80}")
            print(f"Running {len(self.test_suite)} tests...\n")
        
        for i, test_case in enumerate(self.test_suite, 1):
            if verbose:
                print(f"[{i}/{len(self.test_suite)}] {test_case.test_id}: {test_case.description}")
            
            try:
                evaluation = self.run_single_test(test_case)
                self.results.append(evaluation)
                
                if verbose:
                    status = "✅ PASS" if evaluation.passed else "❌ FAIL"
                    print(f"  {status} | Avg Score: {evaluation.get_average_rubric_score():.2f}/5.0")
                    if evaluation.failure_reason:
                        print(f"  Reason: {evaluation.failure_reason}")
            
            except Exception as e:
                print(f"  ❌ ERROR: {str(e)}")
        
        report = EvaluationReport(
            timestamp=datetime.now().isoformat(),
            test_results=self.results,
        )
        
        if verbose:
            self._print_report(report)
        
        return report
    
    def _print_report(self, report: EvaluationReport):
        """Print evaluation report to console."""
        print(f"\n{'='*80}")
        print("EVALUATION RESULTS")
        print(f"{'='*80}\n")
        
        # Summary statistics
        summary = report.to_dict()["summary"]
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed']}")
        print(f"Failed: {summary['failed']}")
        print(f"Pass Rate: {summary['pass_rate']:.1%}\n")
        
        # Category breakdown
        print("Category Breakdown:")
        print(f"{'-'*80}")
        categories = report.get_category_breakdown()
        for cat_name, stats in sorted(categories.items()):
            print(f"{cat_name:30} | Pass Rate: {stats['pass_rate']:.1%} | Avg Score: {stats['avg_score']:.2f}/5.0 ({stats['passed']}/{stats['total']})")
        
        # Rubric scores
        print(f"\n{'-'*80}")
        print("Average Rubric Scores (across all tests):")
        print(f"{'-'*80}")
        rubric_scores = report.get_average_rubric_scores()
        for dimension, score in rubric_scores.items():
            bar = "█" * int(score) + "░" * (5 - int(score))
            print(f"{dimension:30} | {bar} {score:.2f}/5.0")
        
        # Test details
        print(f"\n{'-'*80}")
        print("Detailed Test Results:")
        print(f"{'-'*80}\n")
        
        for result in report.test_results:
            status = "✅" if result.passed else "❌"
            print(f"{status} {result.test_id}: {result.test_case.description}")
            
            if result.passed:
                print(f"   Status: PASSED")
            else:
                print(f"   Status: FAILED - {result.failure_reason}")
            
            print(f"   Automated Metrics:")
            print(f"     - Tool Selection Accuracy: {result.tool_selection_accuracy:.1%}")
            print(f"     - Parameter Extraction: {result.parameter_extraction_accuracy:.1%}")
            print(f"     - Response Completeness: {result.response_completeness:.1%}")
            print(f"     - Hallucination Score: {result.hallucination_score:.2f}")
            print(f"     - Latency: {result.execution_latency_ms:.0f}ms")
            
            print(f"   Rubric Scores:")
            print(f"     - Factual Correctness: {result.factual_correctness.score}/5 - {result.factual_correctness.justification}")
            print(f"     - Tool Use Appropriateness: {result.tool_use_appropriateness.score}/5 - {result.tool_use_appropriateness.justification}")
            print(f"     - Actionability: {result.actionability.score}/5 - {result.actionability.justification}")
            print(f"     - Hallucination: {result.hallucination_detection.score}/5 - {result.hallucination_detection.justification}")
            
            print(f"   Average Rubric Score: {result.get_average_rubric_score():.2f}/5.0")
            print()
    
    def export_report_json(self, filepath: str, report: EvaluationReport):
        """Export evaluation report as JSON."""
        with open(filepath, "w") as f:
            json.dump(report.to_dict(), f, indent=2)
        print(f"Report exported to {filepath}")
    
    def get_success_and_failure_examples(self, report: EvaluationReport, count: int = 2):
        """Get examples of successes and failures for analysis."""
        successes = [r for r in report.test_results if r.passed]
        failures = [r for r in report.test_results if not r.passed]
        
        return {
            "successes": successes[:count],
            "failures": failures[:count],
        }


def run_evaluation():
    """Main evaluation execution."""
    runner = EvaluationRunner()
    report = runner.run_all_tests(verbose=True)
    
    # Export report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = f"outputs/evaluation_report_{timestamp}.json"
    runner.export_report_json(report_path, report)
    
    return report


if __name__ == "__main__":
    report = run_evaluation()
