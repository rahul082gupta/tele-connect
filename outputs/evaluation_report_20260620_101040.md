# Retention Agent Evaluation Report

**Generated**: 2026-06-20T10:10:40.525499

## Summary

- **Total Tests**: 14
- **Passed**: 10
- **Failed**: 4
- **Pass Rate**: 71.4%

## Category Breakdown

| Category | Pass Rate | Avg Score | Tests |
|----------|-----------|-----------|-------|
| Single Tool Happy Path | 0.0% | 4.50/5.0 | 0/1 |
| Multi Step Chaining | 100.0% | 4.50/5.0 | 2/2 |
| Ambiguous Input | 100.0% | 4.00/5.0 | 3/3 |
| Out Of Scope | 50.0% | 3.88/5.0 | 1/2 |
| Escalation Trigger | 66.7% | 3.67/5.0 | 2/3 |
| Model Disagreement | 100.0% | 4.00/5.0 | 1/1 |
| Edge Case | 50.0% | 3.00/5.0 | 1/2 |

## Rubric Scores

- **Factual Correctness**: 3.93/5.0
- **Tool Use Appropriateness**: 4.00/5.0
- **Actionability**: 2.79/5.0
- **Hallucination Detection**: 4.79/5.0

## Test Results


### ❌ T001: Customer lookup by explicit ID
**Status**: FAILED
**Reason**: Poor tool selection accuracy
**Score**: 4.50/5.0

### ✅ T002: Full analysis chain: lookup → predict → offers
**Status**: PASSED
**Score**: 4.50/5.0

### ✅ T003: Multi-step analysis for high-risk customer
**Status**: PASSED
**Score**: 4.50/5.0

### ✅ T004: Missing customer ID - agent should ask for clarification
**Status**: PASSED
**Score**: 4.00/5.0

### ✅ T005: Vague customer reference
**Status**: PASSED
**Score**: 4.00/5.0

### ✅ T006: Partial customer ID
**Status**: PASSED
**Score**: 4.00/5.0

### ❌ T007: Request to modify customer account
**Status**: FAILED
**Reason**: Poor tool selection accuracy
**Score**: 3.75/5.0

### ✅ T008: Request for unrelated information
**Status**: PASSED
**Score**: 4.00/5.0

### ✅ T009: Legal threat escalation
**Status**: PASSED
**Score**: 4.00/5.0

### ✅ T010: Customer complaint and frustration
**Status**: PASSED
**Score**: 4.00/5.0

### ❌ T011: Customer considering competitor switch
**Status**: FAILED
**Reason**: Poor tool selection accuracy
**Score**: 3.00/5.0

### ✅ T012: Low-risk profile with warning signs
**Status**: PASSED
**Score**: 4.00/5.0

### ✅ T013: Very new customer (0 tenure)
**Status**: PASSED
**Score**: 4.00/5.0

### ❌ T014: Extremely long-tenure customer (24+ years)
**Status**: FAILED
**Reason**: Low rubric scores
**Score**: 2.00/5.0
