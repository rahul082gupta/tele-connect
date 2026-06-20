# Quick Reference Guide - Retention Agent

## 🚀 Start Here

### 1. First Time Setup
```bash
# Clone or navigate to project
cd /home/rahul/wipro

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run the Demo
```bash
streamlit run streamlit_agent_app.py
```
Open: http://localhost:8501

### 3. Test the Agent
```python
from src.agent import RetentionAgent
from src.test_suite import get_test_suite

agent = RetentionAgent()
result = agent.process_user_input("Analyze CUST001")
print(result["response"])
```

### 4. Run Evaluation
```bash
python3 run_evaluation.py
# Generates: outputs/evaluation_report_[timestamp].{json,md}
```

---

## 📚 Key Files

| File | Purpose | Key Functions |
|------|---------|---|
| **src/agent.py** | Agent orchestration | `RetentionAgent.process_user_input()` |
| **src/agent_tools.py** | Tool definitions | `execute_tool(name, params)` |
| **src/test_suite.py** | Test cases | `get_test_suite()`, `TestCase` |
| **src/evaluation.py** | Metrics & scoring | `LLMAsJudge.evaluate_test()` |
| **src/evaluation_runner.py** | Test executor | `EvaluationRunner.run_all_tests()` |
| **streamlit_agent_app.py** | Web UI | Run with `streamlit run` |

---

## 🎯 Common Tasks

### Run Single Test
```python
from src.agent import RetentionAgent
from src.test_suite import TEST_SUITE

agent = RetentionAgent()
test = TEST_SUITE[0]  # First test
result = agent.process_user_input(test.user_input)
print(f"Pass: {result['status'] == 'success'}")
```

### Add New Tool
```python
# 1. Define schema in src/agent_tools.py
MY_TOOL_SCHEMA = {
    "name": "my_tool",
    "description": "What it does",
    "parameters": {...}
}

# 2. Implement execute function
def execute_my_tool(params):
    return {"success": True, "data": ...}

# 3. Register in TOOLS dict
TOOLS["my_tool"] = {
    "schema": MY_TOOL_SCHEMA,
    "execute": execute_my_tool,
}

# Done! Automatically available to agent
```

### Add New Test Case
```python
from src.test_suite import TestCase, TestCategory, ExpectedToolCall

test = TestCase(
    test_id="T999",
    category=TestCategory.MULTI_STEP_CHAINING,
    description="Your test description",
    user_input="What user says",
    expected_tool_calls=[
        ExpectedToolCall("tool_name", ["param1", "param2"]),
    ],
    quality_criteria=[
        "Thing 1 should happen",
        "Thing 2 should happen",
    ],
)

# Add to TEST_SUITE list
TEST_SUITE.append(test)
```

### Check Test Results
```python
import json
with open("outputs/evaluation_report_*.json") as f:
    report = json.load(f)
    
print(f"Pass Rate: {report['summary']['pass_rate']:.1%}")
for result in report['test_results']:
    print(f"{result['test_id']}: {'PASS' if result['passed'] else 'FAIL'}")
```

---

## 🔧 Debugging

### Agent Returns No Tools
```python
# Check if customer ID was extracted
from src.agent import RetentionAgent
agent = RetentionAgent()
customer_id = agent._extract_customer_id("Your input")
print(f"Customer ID: {customer_id}")
```

### Tool Execution Failed
```python
from src.agent_tools import execute_tool
result = execute_tool("tool_name", {"param": "value"})
print(result)  # Will show error details
```

### Evaluation Not Running
```bash
# Check dependencies
python3 -c "import pandas, joblib, streamlit; print('OK')"

# Check model exists
ls -la models/churn_model.joblib
```

---

## 📊 Understanding Results

### Evaluation Report Structure
```json
{
  "summary": {
    "total_tests": 14,
    "passed": 10,
    "pass_rate": 0.714
  },
  "category_breakdown": {
    "multi_step_chaining": {
      "total": 2,
      "passed": 2,
      "pass_rate": 1.0,
      "avg_score": 4.5
    }
  },
  "test_results": [
    {
      "test_id": "T001",
      "passed": false,
      "failure_reason": "Poor tool selection accuracy",
      "automated_metrics": {
        "tool_selection_accuracy": 0.25,
        "hallucination_score": 0.0
      },
      "rubric_scores": {
        "factual_correctness": {"score": 4, "justification": "..."},
        ...
      }
    }
  ]
}
```

### Metrics Explained
- **Tool Selection Accuracy** (0-1): Correct tools chosen in right order
- **Parameter Extraction** (0-1): Required parameters present
- **Response Completeness** (0-1): Response has all needed elements
- **Hallucination Score** (0-1): Lower is better; unsupported claims

### Rubric Scores (1-5)
- **1**: Poor/Unacceptable
- **2**: Fair/Needs improvement
- **3**: Good/Acceptable
- **4**: Very good/Strong
- **5**: Excellent/Outstanding

---

## 🚀 Deploy to Production

### Streamlit Cloud (Recommended)
```bash
git push origin main
# Auto-deploys! Check: https://share.streamlit.io
```

### Local Docker
```bash
docker build -t agent .
docker run -p 8501:8501 agent
```

### Railway
```bash
railway login
railway link  # Select your repo
railway up
```

---

## 🎓 Architecture Quick Overview

```
User Input
    ↓
Agent receives message
    ↓
Check escalation? → YES → Escalate to supervisor
    ↓ NO
Extract customer ID? → NO → Ask for customer ID
    ↓ YES
Execute tool chain:
  1. lookup_customer
  2. predict_churn
  3. get_retention_offers
  4. log_interaction
    ↓
Return response with:
  - Analysis
  - Recommendations
  - Next steps
  - Tool call transparency
```

---

## 📞 Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| "Module not found" | `source venv/bin/activate` |
| "Model not found" | Check `models/churn_model.joblib` exists |
| "Streamlit won't start" | `pip install -r requirements.txt` |
| "Evaluation fails" | `python3 -c "import src.agent"` to check syntax |
| "Tests won't run" | Make sure `predict_churn` works: `python3 -c "from src.predict import predict_churn"` |
| "UI looks broken" | Try `streamlit cache clear` |

---

## 📈 Next Steps

1. **Review** `EVALUATION_ANALYSIS.md` for detailed findings
2. **Fix** the 4 failing tests (see specific fixes in analysis)
3. **Deploy** to production (see `DEPLOYMENT_GUIDE.md`)
4. **Monitor** agent performance in real usage
5. **Iterate** with user feedback

---

## 🔗 Documentation Links

- **Architecture**: [PART2_README.md](PART2_README.md)
- **Analysis**: [EVALUATION_ANALYSIS.md](EVALUATION_ANALYSIS.md)
- **Deployment**: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- **Full Project**: [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)
- **Part 1 Model**: [README.md](README.md)

---

## ✅ Checklist for Developers

- [ ] Activated venv: `source venv/bin/activate`
- [ ] Installed deps: `pip install -r requirements.txt`
- [ ] Can run UI: `streamlit run streamlit_agent_app.py`
- [ ] Can run eval: `python3 run_evaluation.py`
- [ ] Model loads: `from src.predict import predict_churn`
- [ ] Agent works: `from src.agent import RetentionAgent`
- [ ] Tests pass: Check `outputs/evaluation_report_*.md`

---

**Last Updated**: June 20, 2026  
**Status**: ✅ Ready for Production
