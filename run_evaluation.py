#!/usr/bin/env python3
"""
Run the complete evaluation suite and generate reports.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.evaluation_runner import EvaluationRunner
from src.test_suite import get_test_summary


def main():
    """Run evaluation and generate reports."""
    print("\n" + "="*80)
    print("RETENTION AGENT EVALUATION SUITE")
    print("="*80 + "\n")
    
    # Show test suite overview
    summary = get_test_summary()
    print(f"📋 Test Suite Overview:")
    print(f"   Total Tests: {summary['total_tests']}")
    print(f"   Categories: {len(summary['by_category'])}")
    for cat, count in summary['by_category'].items():
        print(f"     - {cat}: {count}")
    print()
    
    # Run evaluation
    print("🚀 Starting evaluation...\n")
    runner = EvaluationRunner()
    report = runner.run_all_tests(verbose=True)
    
    # Save report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)
    
    report_path = output_dir / f"evaluation_report_{timestamp}.json"
    runner.export_report_json(str(report_path), report)
    
    # Also save a markdown version
    markdown_path = output_dir / f"evaluation_report_{timestamp}.md"
    with open(markdown_path, "w") as f:
        f.write(_generate_markdown_report(report))
    print(f"\n✅ Reports saved to {output_dir}/")
    
    return report


def _generate_markdown_report(report):
    """Generate a markdown version of the evaluation report."""
    report_dict = report.to_dict()
    summary = report_dict["summary"]
    
    md = f"""# Retention Agent Evaluation Report

**Generated**: {report_dict['timestamp']}

## Summary

- **Total Tests**: {summary['total_tests']}
- **Passed**: {summary['passed']}
- **Failed**: {summary['failed']}
- **Pass Rate**: {summary['pass_rate']:.1%}

## Category Breakdown

| Category | Pass Rate | Avg Score | Tests |
|----------|-----------|-----------|-------|
"""
    
    for cat_name, stats in report.get_category_breakdown().items():
        md += f"| {cat_name.replace('_', ' ').title()} | {stats['pass_rate']:.1%} | {stats['avg_score']:.2f}/5.0 | {stats['passed']}/{stats['total']} |\n"
    
    md += "\n## Rubric Scores\n\n"
    rubric_scores = report.get_average_rubric_scores()
    for dimension, score in rubric_scores.items():
        md += f"- **{dimension.replace('_', ' ').title()}**: {score:.2f}/5.0\n"
    
    md += "\n## Test Results\n\n"
    for result in report.test_results:
        status = "✅" if result.passed else "❌"
        md += f"\n### {status} {result.test_id}: {result.test_case.description}\n"
        md += f"**Status**: {'PASSED' if result.passed else 'FAILED'}\n"
        if result.failure_reason:
            md += f"**Reason**: {result.failure_reason}\n"
        md += f"**Score**: {result.get_average_rubric_score():.2f}/5.0\n"
    
    return md


if __name__ == "__main__":
    report = main()
