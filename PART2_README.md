# Part 2: Retention Agent — Build, Evaluate, Deploy

## Overview

This section implements a complete **retention agent** for TeleConnect that helps customer retention representatives handle at-risk customers in real time. The agent orchestrates multiple tools, predicts churn, recommends retention offers, and recognizes when to escalate.

## Architecture

### Core Components

#### 1. **Agent Orchestration** (`src/agent.py`)
- **RetentionAgent class** implements tool orchestration with:
  - Natural language input processing
  - Tool chaining (lookup → predict → offers → log)
  - Escalation detection (legal threats, cancellation requests)
  - Graceful handling of ambiguous inputs
  - Modular design allowing easy tool addition

**Key Features:**
- Multi-step reasoning with tool dependency management
- Error handling and fallback mechanisms
- Conversation history tracking
- Escalation keyword detection with context awareness

#### 2. **Tool Definitions** (`src/agent_tools.py`)
Five integrated tools with complete schemas and implementations:

| Tool | Purpose | Returns |
|------|---------|---------|
| **predict_churn** | ML model prediction | Churn probability, risk tier, top factors |
| **lookup_customer** | Customer profile retrieval | Demographics, contract, tenure, charges |
| **get_retention_offers** | Filtered offer catalog | Risk tier-specific retention offers |
| **log_interaction** | Interaction recording | Confirmation with log entry ID |
| **escalate_to_supervisor** | Supervisor escalation | Escalation ID and priority confirmation |

**Design Principles:**
- Each tool has explicit schema with required/optional parameters
- Mock implementations backed by realistic test data
- Standardized success/error response format
- Production-realistic parameter requirements

#### 3. **Test Suite** (`src/test_suite.py`)
**14 test cases** covering 7 categories:

1. **Single-Tool Happy Path** (1 test)
   - Basic customer lookup
   
2. **Multi-Step Chaining** (2 tests)
   - Full workflow orchestration
   - High-risk identification
   
3. **Ambiguous Input** (3 tests)
   - Missing customer ID
   - Vague references
   - Partial information
   
4. **Out-of-Scope** (2 tests)
   - Account modifications
   - Unrelated requests
   
5. **Escalation Triggers** (3 tests)
   - Legal threats
   - Angry customers
   - Competitor scenarios
   
6. **Model Disagreement** (1 test)
   - Profile contradictions
   
7. **Edge Cases** (2 tests)
   - New customers
   - Invalid references

**Each test includes:**
- User input scenario
- Expected tool calls (name, order, required parameters)
- Quality criteria for evaluation
- Category classification
- Optional expected outcomes

#### 4. **Evaluation Framework** (`src/evaluation.py`)

**Automated Metrics:**
- **Tool Selection Accuracy** (0-1): Correct tools selected in correct order
- **Parameter Extraction** (0-1): Required parameters properly extracted
- **Response Completeness** (0-1): Response contains all necessary elements
- **Hallucination Score** (0-1): Detects unsupported claims (lower is better)

**LLM-as-Judge Rubric Scoring:**
Each test evaluated on 4 dimensions with 5-level anchored rubrics:

1. **Factual Correctness** (1-5)
   - 1: Multiple factual errors contradicting tool results
   - 3: Mostly correct with minor issues
   - 5: Highly accurate, well-supported, no errors

2. **Tool Use Appropriateness** (1-5)
   - 1: Misused tools, wrong order, missing critical tools
   - 3: Most tools called correctly
   - 5: Perfect orchestration, optimal sequence

3. **Actionability** (1-5)
   - 1: Vague, non-actionable response
   - 3: Some actionable guidance
   - 5: Specific, prioritized, immediate action items

4. **Hallucination Detection** (1-5)
   - 1: Significant fabricated information
   - 3: Mostly grounded, minor unsupported claims
   - 5: No hallucinations, all claims traceable to tools

#### 5. **Evaluation Runner** (`src/evaluation_runner.py`)
Executes all tests and generates:
- Pass/fail status per test
- Aggregate statistics by category
- Average scores by rubric dimension
- Detailed failure analysis
- JSON export for reporting

#### 6. **Streamlit UI** (`streamlit_agent_app.py`)
Live demo interface with three modes:

1. **Live Demo** (Interactive Agent)
   - Chat interface for real-time interaction
   - Visible tool calls and results
   - Conversation history
   - Test customer suggestions

2. **Test Runner**
   - Execute full test suite with progress
   - Category-level filtering
   - Results dashboard with metrics
   - Export reports as JSON

3. **Evaluation Results**
   - Expected outcomes analysis
   - Category breakdown
   - Production roadmap

## Running the System

### 1. Prerequisites
```bash
pip install -r requirements.txt
```

### 2. Live Agent Demo
```bash
streamlit run streamlit_agent_app.py
```
Open browser to `http://localhost:8501`

Select "Live Demo" and try:
- "Check on CUST001"
- "Customer CUST002 is very angry and wants to cancel"
- "I have a high-risk customer on the phone"

### 3. Run Evaluation Suite
In Streamlit app, select "Test Runner" → "Run All Tests"

Or run directly:
```bash
python -c "from src.evaluation_runner import run_evaluation; run_evaluation()"
```

### 4. View Individual Test
```python
from src.agent import RetentionAgent
from src.test_suite import get_test_suite

agent = RetentionAgent()
test = get_test_suite()[0]
result = agent.process_user_input(test.user_input)
print(result)
```

## Design Decisions

### 1. Tool Orchestration Strategy
- **Sequential chaining** with dependency management
- Lookup → Predict → Offers → Log pattern for standard cases
- Early escalation detection for risk cases
- Graceful degradation on missing information

**Rationale:** Reflects real retention rep workflow; avoids unnecessary API calls; escalates appropriately.

### 2. Evaluation Approach
- **Hybrid evaluation**: Automated metrics + LLM-as-judge
- Anchored rubrics with 5 levels (not 1-10 scale)
- Multiple dimensions (not single score)
- Evidence-based scoring

**Rationale:** Provides quantitative rigor + qualitative insight; anchors reduce scorer bias; multiple dimensions capture nuance.

### 3. Mock vs. Real Implementation
- Mock LLM responses with rule-based logic
- Mock customer database with 3 test profiles
- Real churn model from Part 1
- Real tool schemas matching production patterns

**Rationale:** Demonstrates architecture without API dependencies; ready for real LLM integration; evaluable without secrets.

### 4. Modular Tool Design
- Each tool is self-contained with schema + execute function
- TOOLS registry allows dynamic tool addition
- Tool schemas match OpenAI/Anthropic patterns
- Production-ready parameter types

**Rationale:** Easy to add 6th tool without rewriting orchestration; compatible with commercial LLM APIs; extensible.

## Evaluation Results Summary

### Pass Rate Targets
| Category | Expected | Reason |
|----------|----------|--------|
| Single-Tool Happy Path | 100% | Straightforward lookup |
| Multi-Step Chaining | 90% | Complex orchestration may have edge cases |
| Ambiguous Input | 80% | Graceful degradation is hard |
| Out-of-Scope | 85% | Should decline politely |
| Escalation Triggers | 95% | Critical for safety |
| Model Disagreement | 70% | Requires nuanced reasoning |
| Edge Cases | 75% | Unpredictable scenarios |

### Key Metrics
- **Tool Selection Accuracy**: >90% (correct tools for scenario)
- **Response Completeness**: >80% (all required info present)
- **Hallucination Score**: <0.2 (minimal fabrication)
- **Average Rubric Score**: >3.5/5.0 (consistently good)

## LLM-as-Judge Reliability

### Strengths
✅ **Anchored rubrics** reduce bias via specific scoring definitions
✅ **Multiple dimensions** prevent gaming single metric
✅ **Evidence collection** grounds scores in observable facts
✅ **Standardized input** ensures consistent evaluation

### Limitations & Mitigation
⚠️ **Prompt sensitivity**: Use identical prompts for all tests
⚠️ **Positive bias**: Test includes failures and escalations
⚠️ **Hallucination detection**: Mock LLM checks for obvious issues; real LLM would do better

### Inter-Rater Consistency
- All tests use same rubric and anchors
- Scoring logic is deterministic (not random)
- Evidence-based justifications logged
- Could be validated with human review of 10% of tests

## Failure Case Analysis Template

For each failed test, document:

1. **What Failed**: Tool not called, wrong parameters, incomplete response
2. **Root Cause**: Agent logic flaw, tool schema issue, edge case handling
3. **Impact**: Affects which scenarios
4. **Fix**: Code change, prompt adjustment, tool modification
5. **Prevention**: Add test, validate earlier, improve docs

## Production Roadmap

### Phase 1: CI/CD Integration (Week 1-2)
```bash
# On every commit:
- Run evaluation suite (5min)
- Check pass rate ≥ 85%
- Track metrics over time
- Alert on regressions >5%
```

### Phase 2: Real LLM Integration (Week 3-4)
```python
# Replace mock_llm_response() with:
from anthropic import Anthropic
client = Anthropic()
response = client.messages.create(
    model="claude-3-5-sonnet",
    tools=[tool["schema"] for tool in TOOLS.values()],
    ...
)
```

### Phase 3: Load Testing & Monitoring (Week 5-6)
- Simulate 1000 concurrent retention reps
- Monitor latency, error rates, tool success
- Set SLOs (e.g., p99 latency <2s, error rate <1%)
- Auto-scale based on queue depth

### Phase 4: Human Feedback Loop (Week 7-8)
- Collect retention rep feedback on recommendations
- Track offer acceptance rates
- Retrain on high-performing scenarios
- Update evaluation thresholds based on real outcomes

### Phase 5: Advanced Features (Ongoing)
- Multi-turn negotiation with customer
- Personalized offer optimization
- Competitor analysis integration
- Regulatory compliance checking
- Sentiment analysis for tone adjustment

## File Structure

```
wipro/
├── src/
│   ├── agent.py                 # Core agent orchestration
│   ├── agent_tools.py           # Tool definitions and implementations
│   ├── test_suite.py            # 14 test cases
│   ├── evaluation.py            # Metrics + LLM-as-judge
│   ├── evaluation_runner.py     # Test executor
│   └── predict.py               # Part 1 churn model
│
├── streamlit_agent_app.py       # Live demo UI
├── streamlit_app.py             # Part 1 UI (kept for reference)
└── README.md                    # This file
```

## Deployment

### Option 1: Streamlit Cloud (Recommended)
```bash
git push
# Streamlit Cloud auto-deploys from GitHub
# Set secrets: None required (uses mock data)
# URL: https://[username]-[app-name].streamlit.app
```

### Option 2: Railway / Render
```bash
# Connect to GitHub repo
# Select streamlit_agent_app.py as main file
# Deploy
```

### Option 3: Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["streamlit", "run", "streamlit_agent_app.py"]
```

## Testing Locally

```bash
# Run single test
python -c "
from src.agent import RetentionAgent
from src.test_suite import get_test_suite

agent = RetentionAgent()
test = get_test_suite()[1]  # Multi-step test
result = agent.process_user_input(test.user_input)
print('Response:', result['response'][:200])
print('Tools:', [tc['tool'] for tc in result['tool_calls']])
"

# Run evaluation
python src/evaluation_runner.py
```

## Key Takeaways

1. **Modular Design**: Adding a 6th tool requires only registering it in TOOLS dict
2. **Robust Evaluation**: Multiple metrics + anchored rubrics > single score
3. **Graceful Degradation**: Agent asks for missing info rather than guessing
4. **Safety-First**: Escalation triggers are explicit and conservative
5. **Production-Ready**: Schemas match real LLM APIs; ready for integration

---

**Status**: ✅ Complete architecture with working demo, evaluation suite, and deployment instructions.

**Time Budget Used**: ~3-4 hours (Agent design + Tools + Tests + Evaluation + UI)

**Next Steps**: Integrate real LLM API (OpenAI/Anthropic) and deploy to production.
